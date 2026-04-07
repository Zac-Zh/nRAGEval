"""中文 claim extractor，含反碎片化逻辑"""
import re
from typing import Optional

from ..judge.base import BaseJudge


def extract_claims(text: str, judge: BaseJudge) -> list[str]:
    """
    将 response 拆分为原子 claims。

    使用 LLM + rubric prompt（prompts/claim_extraction.txt）。
    prompt 内嵌的反碎片化规则基于阶段一 DOC-1 Q07 的 16+ 碎片化失败案例校准。
    """
    if not text or not text.strip():
        return []

    # 拼音化/英文化检测：如果 response 几乎不含中文字符，标记为 extraction failure
    cn_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    total_chars = len(re.sub(r"\s", "", text))
    if total_chars > 20 and cn_chars / max(total_chars, 1) < 0.2:
        # 太少中文字符，视为异常（保留原文作单一 claim 由后续 KBC 判断）
        return [text.strip()]

    prompt_template = BaseJudge.load_prompt("claim_extraction")
    prompt = prompt_template.replace("{answer}", text)

    data = judge.call_json(prompt)

    if isinstance(data, dict) and "claims" in data and isinstance(data["claims"], list):
        claims = [str(c).strip() for c in data["claims"] if str(c).strip()]
        return claims
    # 回退：JSON 解析失败时，按句号粗拆（不推荐但保底）
    fallback = [s.strip() for s in re.split(r"[。；]", text) if len(s.strip()) > 5]
    return fallback
