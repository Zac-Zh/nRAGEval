"""Answer Completeness (AC) — 回答完整性"""
from ..judge.base import BaseJudge
from ..schemas import EvalSample


def evaluate_ac(sample: EvalSample, judge: BaseJudge) -> dict:
    """
    评估 AC:
    1. 分解 question 为要点列表
    2. 检查 response 是否覆盖每个要点
    3. AC = (covered + 0.5 * partial) / total
    """
    prompt_template = BaseJudge.load_prompt("ac_rubric")
    prompt = prompt_template.replace("{question}", sample.question).replace("{answer}", sample.answer)

    result = judge.call_json(prompt)
    if not isinstance(result, dict):
        return {"score": None, "error": "judge 返回格式错误"}

    score = result.get("score")
    if isinstance(score, (int, float)):
        score = float(score)
    else:
        # 自己计算
        required = result.get("required_points", [])
        covered = result.get("covered_points", [])
        partial = result.get("partially_covered_points", [])
        total = len(required)
        if total > 0:
            score = round((len(covered) + 0.5 * len(partial)) / total, 4)
        else:
            score = None

    return {
        "score": score,
        "required_points": result.get("required_points", []),
        "covered_points": result.get("covered_points", []),
        "partially_covered_points": result.get("partially_covered_points", []),
        "not_covered_points": result.get("not_covered_points", []),
        "note": result.get("note", ""),
    }
