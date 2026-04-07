"""Qwen-Plus judge 实现（via DashScope OpenAI-compatible API）"""
import os
from .base import BaseJudge


class QwenJudge(BaseJudge):
    name = "qwen-plus"

    def __init__(self, model: str = "qwen-plus", **kwargs):
        super().__init__(model=model, **kwargs)
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY not set in environment")
        from openai import OpenAI
        self.client = OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
        )

    def _call_api(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content or ""
