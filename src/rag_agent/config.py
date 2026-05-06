
"""全局配置文件。

这个项目的配置统一从 `.env` 或系统环境变量读取。
这样做的好处：
1. 代码里不写死 API Key，避免泄露。
2. 同一套代码可以在本地、服务器、Docker 环境里复用。
3. chunk、top_k、阈值这些 RAG 调参项可以不改代码直接调。
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env.

    BaseSettings 会自动读取环境变量。
    例如这里的 `openai_api_key` 会对应 `.env` 里的 `OPENAI_API_KEY`。
    """

    # env_file 表示启动项目时自动读取根目录下的 .env 文件。
    # extra="ignore" 表示 .env 中出现没定义的变量也不会报错。
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ===== 大模型配置 =====
    # 这里使用 OpenAI-compatible API：OpenAI、DeepSeek、Qwen、OneAPI、硅基流动等都可以套这个格式。
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"

    # ===== 向量数据库 Qdrant 配置 =====
    # Qdrant 存的是 chunk 的 embedding 向量，用于语义检索。
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "rag_chunks"

    # ===== SQLite 配置 =====
    # SQLite 这里承担两个职责：
    # 1. 存 chunk 原文和元数据。
    # 2. 用 FTS5 做关键词检索，和向量检索组成 hybrid search。
    sqlite_path: Path = Path("storage/rag.db")

    # ===== Embedding / Reranker 模型 =====
    # embedding_model：把文本转成向量。中文资料建议 bge-small-zh-v1.5 或 bge-m3。
    # reranker_model：对初步召回的 chunk 做二次排序，通常比只看向量相似度更准。
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    enable_reranker: bool = True

    # ===== Chunk 切分参数 =====
    # chunk_size 太小：语义不完整；太大：召回不准、上下文浪费。
    # chunk_overlap 用来保留相邻 chunk 的衔接信息，避免一句话被切断后丢上下文。
    chunk_size: int = 900
    chunk_overlap: int = 150

    # ===== 检索参数 =====
    # dense_top_k：向量检索召回多少条。
    # sparse_top_k：关键词检索召回多少条。
    # fusion_top_k：RRF 融合后保留多少条交给 reranker。
    # rerank_top_k：最终给 LLM 的证据条数。
    dense_top_k: int = 40
    sparse_top_k: int = 40
    fusion_top_k: int = 20
    rerank_top_k: int = 8

    # RRF 的 k 是平滑参数。一般 60 是常用默认值。
    rrf_k: int = 60

    # 证据门控阈值。
    # RRF 分数通常只有 0.01-0.04 左右；CrossEncoder 分数又和模型有关。
    # 所以默认值不要太高，否则容易“检索到了但误判证据不足”。
    # 真正项目里应该用 scripts/eval_retrieval.py 基于自己的数据集调。
    min_relevance_score: float = 0.01

    # 低 temperature 可以降低胡编概率，让回答更稳定。
    temperature: float = 0.1

    # 拼给 LLM 的上下文最大字符数。太大成本高、慢；太小证据可能不够。
    max_context_chars: int = 9000


# 全项目直接 import settings 使用，避免每个模块重复读取 .env。
settings = Settings()
