
"""大模型调用封装。

本项目把 LLM 调用单独封装成 LLMClient，而不是在 Agent 里直接写 OpenAI 调用。
这样以后更容易替换模型：OpenAI、DeepSeek、Qwen、Moonshot、OneAPI 都可以复用。
"""

from __future__ import annotations

from openai import OpenAI

from rag_agent.config import settings


class LLMClient:
    """OpenAI-compatible chat client。"""

    def __init__(self):
        # 没配置 Key 时，不直接让程序崩溃。
        # 这样你仍然可以测试 ingestion / retrieval 链路。
        self.enabled = bool(settings.openai_api_key)
        self.client: OpenAI | None = None
        if self.enabled:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        """调用聊天模型。

        messages 是 OpenAI Chat Completions 的标准格式：
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """

        if not self.enabled or self.client is None:
            return (
                "未配置 OPENAI_API_KEY，因此无法调用大模型生成最终回答。"
                "检索链路仍可运行；请在 .env 中配置 OPENAI_API_KEY、OPENAI_BASE_URL 和 CHAT_MODEL。"
            )

        resp = self.client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            temperature=settings.temperature if temperature is None else temperature,
        )
        return resp.choices[0].message.content or ""
