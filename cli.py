"""nrageval — 面向中文 RAG 的评测框架，来源合法性优先于答案正确性"""
from .schemas import EvalSample, EvalResult, CounterfactualTest, BidirectionalTest
from .evaluator import evaluate
from .presets import (
    SCENE_PRESETS,
    evaluate_against_preset,
    compare_with_baseline,
    determine_signal,
)

__version__ = "0.1.0"
__all__ = [
    "EvalSample",
    "EvalResult",
    "CounterfactualTest",
    "BidirectionalTest",
    "evaluate",
    "SCENE_PRESETS",
    "evaluate_against_preset",
    "compare_with_baseline",
    "determine_signal",
]
