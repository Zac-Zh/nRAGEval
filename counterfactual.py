"""nrageval CLI"""
import json
import os
import sys

import click

from .schemas import EvalSample, CounterfactualTest, BidirectionalTest
from .evaluator import evaluate as run_evaluate
from .judge import get_judge
from .generators import (
    generate_counterfactual_tests,
    generate_bidirectional_tests,
    run_counterfactual_test,
)
from .report import render_html_report


def _load_samples(path: str) -> list[dict]:
    """从 .json 或 .jsonl 加载样本"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if content.startswith("["):
        return json.loads(content)
    # JSONL
    return [json.loads(line) for line in content.splitlines() if line.strip()]


@click.group()
def cli():
    """nrageval — 面向中文 RAG 的评测框架"""
    pass


@cli.command()
@click.option("--data", required=True, help="RAG pipeline 输出 .json/.jsonl")
@click.option("--metrics", default="kbc,ra,ct,ncp,ac", help="指标列表，逗号分隔")
@click.option("--judge", default="deepseek-chat", help="judge 模型，双 judge 用逗号分隔")
@click.option("--output", default="report/eval_report.html", help="HTML 报告输出路径")
@click.option("--scene", default=None, type=click.Choice(["policy", "technical", "faq"]),
              help="场景预设：启用场景及格线判断 + 信号灯")
@click.option("--baseline", default=None, help="baseline JSON 路径（如 data/baseline/naive_rag_baseline.json）")
@click.option("--save-json", default=None, help="同时保存原始评测结果 JSON")
def evaluate(data, metrics, judge, output, scene, baseline, save_json):
    """对 RAG 输出跑 5 维评测，生成 HTML 报告"""
    click.echo(f"加载数据: {data}")
    samples = _load_samples(data)
    click.echo(f"共 {len(samples)} 条")

    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    judge_list = [j.strip() for j in judge.split(",") if j.strip()]
    judge_arg = judge_list if len(judge_list) > 1 else judge_list[0]

    click.echo(f"指标: {metric_list}")
    click.echo(f"Judge: {judge_list}")
    if scene:
        click.echo(f"场景预设: {scene}")
    if baseline:
        click.echo(f"Baseline: {baseline}")

    # 加载 baseline（如果提供）
    baseline_data = None
    if baseline:
        with open(baseline, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)

    results = run_evaluate(samples, metrics=metric_list, judge=judge_arg)

    if save_json:
        with open(save_json, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, ensure_ascii=False, indent=2, default=str)
        click.echo(f"原始结果已保存到 {save_json}")

    out = render_html_report(results, output, scene=scene, baseline=baseline_data)
    click.echo(f"HTML 报告已生成: {out}")


@cli.command()
@click.option("--knowledge-base", required=True, help="知识库目录或文件")
@click.option("--judge", default="deepseek-chat")
@click.option("--num-samples", default=20, type=int)
@click.option("--output", required=True, help="反事实测试集输出 .jsonl")
def counterfactual(knowledge_base, judge, num_samples, output):
    """从知识库自动生成反事实合规测试集"""
    click.echo(f"读取知识库: {knowledge_base}")
    j = get_judge(judge)
    tests = generate_counterfactual_tests(knowledge_base, j, num_samples=num_samples)
    click.echo(f"生成 {len(tests)} 条反事实测试")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for t in tests:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
    click.echo(f"已保存到 {output}")


@cli.command()
@click.option("--knowledge-base", required=True)
@click.option("--judge", default="deepseek-chat")
@click.option("--num-samples", default=20, type=int)
@click.option("--output", required=True)
def bidirectional(knowledge_base, judge, num_samples, output):
    """从知识库自动生成双向一致性测试集"""
    click.echo(f"读取知识库: {knowledge_base}")
    j = get_judge(judge)
    tests = generate_bidirectional_tests(knowledge_base, j, num_samples=num_samples)
    click.echo(f"生成 {len(tests)} 条双向测试")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for t in tests:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
    click.echo(f"已保存到 {output}")


@cli.command("test-counterfactual")
@click.option("--tests", required=True, help="反事实测试集 .jsonl")
@click.option("--pipeline-output", required=True, help="RAG pipeline 跑完反事实测试集的输出")
@click.option("--output", required=True, help="报告输出路径")
def test_counterfactual(tests, pipeline_output, output):
    """跑反事实测试（无需 LLM judge，纯规则匹配）"""
    click.echo(f"加载测试集: {tests}")
    tests_list = []
    with open(tests, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                tests_list.append(CounterfactualTest.from_dict(json.loads(line)))

    click.echo(f"加载 pipeline 输出: {pipeline_output}")
    pipeline_data = _load_samples(pipeline_output)

    results = run_counterfactual_test(tests_list, pipeline_data)

    # 统计
    counts = {}
    for r in results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    click.echo(f"反事实测试结果统计: {counts}")

    # 保存 JSON + 简单 HTML
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    if output.endswith(".html"):
        html = _render_counterfactual_html(results, counts)
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
    else:
        with open(output, "w", encoding="utf-8") as f:
            json.dump({"counts": counts, "results": results}, f, ensure_ascii=False, indent=2)
    click.echo(f"结果已保存: {output}")


def _render_counterfactual_html(results, counts):
    rows = ""
    for r in results:
        t = r.get("test", {})
        res = r.get("result", "-")
        color = {"pass": "#d4edda", "pass_refusal": "#d1ecf1", "fail_memory_leak": "#f8d7da",
                 "pass_with_disclaimer": "#d4edda", "ambiguous": "#fff3cd", "not_run": "#eee"}.get(res, "#eee")
        rows += f"""
        <tr style='background:{color};'>
          <td>{t.get('question', '')}</td>
          <td>{t.get('original_fact', '')}</td>
          <td>{t.get('counterfactual_fact', '')}</td>
          <td>{r.get('answer', '')[:200]}</td>
          <td>{res}</td>
          <td>{r.get('reason', '')}</td>
        </tr>
        """
    counts_html = " · ".join(f"{k}: {v}" for k, v in counts.items())
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>反事实测试报告</title>
<style>body{{font-family:sans-serif;max-width:1400px;margin:20px auto;}}
table{{border-collapse:collapse;width:100%;}} th,td{{border:1px solid #ccc;padding:8px;}}</style></head>
<body><h1>反事实合规测试报告</h1><p>结果统计: {counts_html}</p>
<table><thead><tr><th>问题</th><th>原始事实</th><th>反事实</th><th>回答</th><th>结果</th><th>说明</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""


if __name__ == "__main__":
    cli()
