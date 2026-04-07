"""反事实合规测试生成器"""
import json
import os
from typing import Optional

from ..judge.base import BaseJudge
from ..judge.rule_based import RuleBasedJudge
from ..schemas import CounterfactualTest


def generate_counterfactual_tests(
    knowledge_base_path: str,
    judge: BaseJudge,
    num_samples: int = 20,
) -> list[CounterfactualTest]:
    """
    从知识库文档中自动生成反事实测试用例。

    Args:
        knowledge_base_path: 知识库目录或单文件路径
        judge: 用于生成的 LLM judge
        num_samples: 总样本数

    Returns:
        CounterfactualTest 列表
    """
    # 读取文档
    documents = _load_documents(knowledge_base_path)
    if not documents:
        raise ValueError(f"未在 {knowledge_base_path} 找到任何文档")

    # 将 num_samples 按文档数平均分配
    per_doc = max(1, num_samples // len(documents))
    prompt_template = BaseJudge.load_prompt("counterfactual_gen")

    tests = []
    for doc_id, text in documents.items():
        # 限制文档长度以控制 token 消耗
        doc_text = text[:4000] if len(text) > 4000 else text
        prompt = prompt_template.replace("{num_samples}", str(per_doc)).replace("{document}", doc_text)
        raw = judge.call_json(prompt)

        # 兼容返回 {"_array": [...]} 或直接数组/对象
        items = []
        if isinstance(raw, dict):
            if "_array" in raw:
                items = raw["_array"]
            elif "tests" in raw:
                items = raw["tests"]
            elif "counterfactual_fact" in raw:
                items = [raw]

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                tests.append(CounterfactualTest(
                    original_fact=item.get("original_fact", ""),
                    counterfactual_fact=item.get("counterfactual_fact", ""),
                    question=item.get("question", ""),
                    expected_answer_contains=item.get("expected_answer_contains", ""),
                    boundary_violation_signal=item.get("boundary_violation_signal", ""),
                    source_doc_id=doc_id,
                ))
            except Exception:
                continue

        if len(tests) >= num_samples:
            break

    return tests[:num_samples]


def run_counterfactual_test(
    tests: list[CounterfactualTest],
    pipeline_outputs: list[dict],
) -> list[dict]:
    """
    用反事实测试评估 RAG pipeline 的输出（不调用 LLM）。

    pipeline_outputs 每条应含 {"question", "answer"} 字段。
    按 question 字面匹配关联到 test。
    """
    # 以 question 作为 key 建立查表
    output_by_q = {o["question"].strip(): o for o in pipeline_outputs}

    results = []
    for t in tests:
        if t.question.strip() not in output_by_q:
            results.append({
                "test": t.to_dict(),
                "result": "not_run",
                "reason": "pipeline 输出中找不到对应问题",
            })
            continue
        output = output_by_q[t.question.strip()]
        answer = output.get("answer") or output.get("generated_answer", "")
        verdict = RuleBasedJudge.check_counterfactual(
            answer=answer,
            expected_answer_contains=t.expected_answer_contains,
            boundary_violation_signal=t.boundary_violation_signal,
        )
        results.append({
            "test": t.to_dict(),
            "answer": answer,
            "result": verdict["result"],
            "reason": verdict["reason"],
        })

    return results


def _load_documents(path: str) -> dict:
    """从目录或单文件加载文档"""
    docs = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            docs[os.path.basename(path)] = f.read()
        return docs
    # 目录：读取所有 .txt 文件
    for fname in sorted(os.listdir(path)):
        if fname.endswith(".txt"):
            with open(os.path.join(path, fname), "r", encoding="utf-8") as f:
                docs[fname] = f.read()
    return docs
