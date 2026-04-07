"""Judge 基类：所有 LLM judge 的统一接口"""
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "prompts")


class BaseJudge(ABC):
    """Judge 基类，包含统一的 retry + rate limiting + prompt 加载"""

    name: str = "base"

    def __init__(self, model: str, max_retries: int = 3, min_interval: float = 1.0, max_tokens: int = 4096):
        self.model = model
        self.max_retries = max_retries
        self.min_interval = min_interval
        self.max_tokens = max_tokens
        self._last_call_time = 0.0

    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        """子类实现实际的 API 调用，返回 raw text response"""
        ...

    def _rate_limit(self):
        """速率限制：确保两次调用间至少间隔 min_interval 秒"""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_time = time.time()

    def call(self, prompt: str) -> str:
        """带 retry 和 rate limiting 的 API 调用"""
        last_err = None
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                return self._call_api(prompt)
            except Exception as e:
                last_err = e
                if attempt < self.max_retries - 1:
                    time.sleep((attempt + 1) * 2)
        raise RuntimeError(f"Judge {self.name} failed after {self.max_retries} retries: {last_err}")

    def call_json(self, prompt: str) -> dict:
        """调用并解析 JSON 输出。失败则返回 {"_parse_error": True, "raw": ...}"""
        text = self.call(prompt)
        return self._extract_json(text)

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON 对象"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except Exception:
            pass
        # 去除 markdown code fence
        cleaned = text.strip()
        if "```" in cleaned:
            import re
            m = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
        # 定位第一个 { 到最后一个 }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                pass
        # 尝试数组
        start_a = cleaned.find("[")
        end_a = cleaned.rfind("]")
        if start_a >= 0 and end_a > start_a:
            try:
                return {"_array": json.loads(cleaned[start_a:end_a + 1])}
            except Exception:
                pass
        return {"_parse_error": True, "raw": text[:500]}

    @staticmethod
    def load_prompt(name: str) -> str:
        """加载 prompts/ 下的 rubric 模板"""
        path = os.path.join(PROMPT_DIR, f"{name}.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
