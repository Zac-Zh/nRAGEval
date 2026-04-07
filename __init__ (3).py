"""统一评测入口 —— evaluate() 接收一批 EvalSample 并返回 EvalResult 列表"""
from typing import Optional, Union

from .schemas import EvalSample, EvalResult
from .judge import get_judge, BaseJudge
from .metrics import METRIC_FUNCTIONS

DEFAULT_METRICS = ["kbc", "ra", "ct", "ncp", "ac"]


def evaluate(
    samples: list[Union[EvalSample, dict]],
    metrics: Optional[list[str]] = None,
    judge: Union[str, BaseJudge, list] = "deepseek-chat",
    low_confidence_threshold: float = 0.3,
    verbose: bool = True,
) -> list[EvalResult]:
    """
    主评测入口。

    Args:
        samples: EvalSample 列表（也接受 dict）
        metrics: 要评测的指标名列表，默认 ["kbc","ra","ct","ncp","ac"]
        judge: 单 judge 名称/实例，或双 judge 列表（开启 low_confidence 检测）
        low_confidence_threshold: 两 judge 差值超过此值时标记 low_confidence
        verbose: 打印进度

    Returns:
        list[EvalResult]
    """
    if metrics is None:
        metrics = DEFAULT_METRICS

    # normalize samples
    normalized = []
    for s in samples:
        if isinstance(s, dict):
            normalized.append(EvalSample.from_dict(s))
        else:
            normalized.append(s)

    # normalize judges —— 支持双 judge 模式
    dual_judge = False
    if isinstance(judge, list):
        if len(judge) == 1:
            judges = [judge[0] if isinstance(judge[0], BaseJudge) else get_judge(judge[0])]
        elif len(judge) >= 2:
            judges = [j if isinstance(j, BaseJudge) else get_judge(j) for j in judge[:2]]
            dual_judge = True
        else:
            raise ValueError("judge list 不能为空")
    elif isinstance(judge, BaseJudge):
        judges = [judge]
    else:
        judges = [get_judge(judge)]

    primary_judge = judges[0]
    results = []

    for i, sample in enumerate(normalized):
        if verbose:
            print(f"  [{i+1}/{len(normalized)}] {sample.question[:50]}")

        scores = {}
        details = {}
        primary_scores = {}

        for metric in metrics:
            if metric not in METRIC_FUNCTIONS:
                continue
            try:
                fn = METRIC_FUNCTIONS[metric]
                result = fn(sample, primary_judge)
                scores[metric] = result.get("score")
                details[metric] = result
                primary_scores[metric] = result.get("score")
            except Exception as e:
                scores[metric] = None
                details[metric] = {"error": str(e)[:300]}

        confidence = "high"
        if dual_judge:
            # 用第二个 judge 跑一遍，比对差异
            secondary_scores = {}
            for metric in metrics:
                if metric not in METRIC_FUNCTIONS:
                    continue
                try:
                    fn = METRIC_FUNCTIONS[metric]
                    result = fn(sample, judges[1])
                    secondary_scores[metric] = result.get("score")
                    details.setdefault(f"{metric}_secondary", result)
                except Exception as e:
                    secondary_scores[metric] = None

            # 合并分数：取平均，标记 low_confidence
            merged = {}
            for m in metrics:
                a = primary_scores.get(m)
                b = secondary_scores.get(m)
                if a is None and b is None:
                    merged[m] = None
                elif a is None:
                    merged[m] = b
                elif b is None:
                    merged[m] = a
                else:
                    merged[m] = round((a + b) / 2, 4)
                    if abs(a - b) > low_confidence_threshold:
                        confidence = "low"
                        details.setdefault("low_confidence_metrics", []).append(m)
            scores = merged

        results.append(EvalResult(
            sample=sample,
            scores=scores,
            details=details,
            judge_model=",".join(j.name for j in judges),
            confidence=confidence,
        ))

    return results
