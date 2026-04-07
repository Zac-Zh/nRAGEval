from .base import BaseJudge
from .deepseek import DeepSeekJudge
from .qwen import QwenJudge
from .rule_based import RuleBasedJudge


def get_judge(name: str) -> BaseJudge:
    """按名称获取 judge 实例"""
    name = name.lower()
    if name in ("deepseek", "deepseek-chat"):
        return DeepSeekJudge()
    if name in ("qwen", "qwen-plus"):
        return QwenJudge()
    if name in ("rule", "rule_based", "rule-based"):
        return RuleBasedJudge()
    raise ValueError(f"Unknown judge: {name}")


__all__ = ["BaseJudge", "DeepSeekJudge", "QwenJudge", "RuleBasedJudge", "get_judge"]
