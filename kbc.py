"""DeepSeek-Chat judge 实现"""
import os
from .base import BaseJudge


class DeepSeekJudge(BaseJudge):
    name = "deepseek-chat"

    def __init__(self, model: str = "deepseek-chat", **kwargs):
        super().__init__(model=model, **kwargs)
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in environment")
        from openai import OpenAI
        self.client = OpenAI(
            base_url="https://api.deepseek.com/v1",
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
