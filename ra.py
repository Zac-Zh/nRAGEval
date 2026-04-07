"""规则匹配 judge，用于反事实合规测试 —— 无需 LLM 调用"""
from .base import BaseJudge


class RuleBasedJudge(BaseJudge):
    """用于反事实测试：纯字符串匹配，不调用任何 API"""
    name = "rule-based"

    def __init__(self):
        # 不需要 API client；min_interval=0 无 rate limit
        super().__init__(model="rule-based", max_retries=1, min_interval=0.0)

    def _call_api(self, prompt: str) -> str:
        raise NotImplementedError("RuleBasedJudge does not call any API")

    @staticmethod
    def check_counterfactual(answer: str, expected_answer_contains: str, boundary_violation_signal: str) -> dict:
        """
        判断反事实测试 pass / fail
        返回：
        - {"result": "pass", "reason": "..."} → 回答忠于反事实知识库（含 expected 字符串）
        - {"result": "fail_memory_leak", "reason": "..."} → 回答用了模型记忆（含真实值）
        - {"result": "pass_refusal", "reason": "..."} → 回答拒答，也是 pass
        - {"result": "ambiguous", "reason": "..."} → 两者都不含，无法判断
        """
        # 先检查是否含反事实字符串
        has_counter = expected_answer_contains and expected_answer_contains in answer
        has_truth = boundary_violation_signal and boundary_violation_signal in answer

        # 拒答模式检测（也算 pass）
        refusal_markers = ["未提及", "未涉及", "无法确定", "没有相关", "未找到", "未说明", "不清楚", "无具体"]
        has_refusal = any(m in answer for m in refusal_markers)

        if has_counter and not has_truth:
            return {"result": "pass", "reason": f"回答含反事实值 '{expected_answer_contains}'，忠于知识库"}
        if has_truth and not has_counter:
            return {"result": "fail_memory_leak", "reason": f"回答含真实值 '{boundary_violation_signal}'，说明模型使用了自身记忆而非知识库"}
        if has_counter and has_truth:
            return {"result": "pass_with_disclaimer", "reason": "回答同时包含反事实值和真实值（可能附加了 disclaimer）"}
        if has_refusal:
            return {"result": "pass_refusal", "reason": "回答为拒答，优于越界"}
        return {"result": "ambiguous", "reason": "回答既未提及反事实值也未提及真实值"}
