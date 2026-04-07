"""Citation Traceability (CT) — 引用可追溯性"""
from ..judge.base import BaseJudge
from ..schemas import EvalSample


def evaluate_ct(sample: EvalSample, judge: BaseJudge) -> dict:
    """
    评估 CT:
    1.0 显式引用且正确
    0.7 可追溯但无显式引用
    0.5 引用编号正确但内容偏差
    0.3 多段拼凑/模糊
    0.0 引用错误或不可追溯
    """
    prompt_template = BaseJudge.load_prompt("ct_rubric")
    ctx_text = "\n---\n".join(f"[{i+1}] {c}" for i, c in enumerate(sample.contexts))
    prompt = prompt_template.replace("{answer}", sample.answer).replace("{contexts}", ctx_text)

    result = judge.call_json(prompt)
    if not isinstance(result, dict) or "score" not in result:
        return {
            "score": None,
            "error": "judge 返回格式错误",
            "raw": str(result)[:200],
        }

    try:
        score = float(result["score"])
    except (TypeError, ValueError):
        score = None

    return {
        "score": score,
        "has_explicit_citation": result.get("has_explicit_citation"),
        "citation": result.get("citation"),
        "verified": result.get("verified"),
        "reasoning": result.get("reasoning", ""),
    }
