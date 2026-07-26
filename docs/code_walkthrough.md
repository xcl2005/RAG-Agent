# 代码阅读路线

建议按“合同 → 入库 → 检索 → Agent → API”的顺序阅读，而不是从目录逐文件扫。

## 1. 配置和数据合同

- `src/rag_agent/config.py`：所有环境配置、数值边界和跨字段校验。
- `src/rag_agent/schemas.py`：`RawDocument`、`Chunk`、`Candidate` 与证据判断结构。
- `.env.example`：本地运行的完整配置面。

先注意 `Candidate.score` 的约定：它总是 `[0, 1]`，各后端原始分数保存在
`dense_score`、`sparse_score`、`fusion_score` 和 `rerank_score`。

## 2. 文档入库

入口是 `src/rag_agent/ingest/indexer.py`：

```text
iter_files
  -> load_document
  -> chunk_documents
  -> Qdrant upsert new vectors
  -> SQLite transaction: chunks + FTS + document manifest
  -> best-effort delete stale vectors
```

配套文件：

- `loaders.py`：TXT/Markdown/PDF/DOCX/HTML 解析与来源元数据。
- `chunker.py`：标题/页面元数据继承、最大长度和 overlap。
- `sqlite_store.py`：WAL、FTS5、document manifest 与按文档原子替换。
- `vector_store.py`：懒加载 embedding、collection 维度校验和 Qdrant payload。

先看 `tests/test_indexer.py`，能最快理解为什么写入顺序这样安排。

## 3. 混合检索

`src/rag_agent/retrieval/hybrid.py` 的 `retrieve_many()` 是核心：

1. 去重查询变体并给原问题最高权重。
2. 每个查询分别调用 Qdrant 与 SQLite FTS5。
3. 单后端失败时记录 `backend_errors` 并使用剩余后端。
4. `fusion.py` 用 weighted RRF 融合排名并归一化。
5. 回 SQLite 批量读取权威原文。
6. `reranker.py` 可选加载 CrossEncoder；不可用时回退到 fusion 排名。

对应测试是 `test_hybrid.py`、`test_rrf.py` 和 `test_vector_store.py`。

## 4. Agent 状态图

`src/rag_agent/agent/graph.py` 值得重点阅读：

```text
initialize
  -> plan_queries
  -> retrieve
  -> grade_evidence
     -> retry plan (bounded)
     -> abstain
     -> generate_answer
  -> validate_citations
     -> repair once
     -> citation_failure
     -> finalize
```

- `llm/client.py` 只负责 Responses / Chat Completions 传输和结构化输出，不拥有第二套 Agent loop。
- `prompts.py` 构造模型真正看到的证据，并确保返回来源与上下文一致。
- `guardrails.py` 负责输入清洗、注入信号和引用编号验证。
- `SqliteSaver` 按 `thread_id` 保存状态；目前用于持久化多轮，不等同于完整的任务恢复产品。

对应测试是 `test_agent_graph.py`、`test_llm_client.py`、`test_prompts.py` 和
`test_guardrails.py`。

## 5. API、UI 与 MCP

- `api/main.py`：lifespan 资源复用、鉴权、聊天、SSE、安全上传和后台任务。
- `api/jobs.py`：单进程内存任务状态；不是持久化队列。
- `api/models.py`：OpenAPI 请求/响应合同。
- `web/`：原生 HTML/CSS/JS；问答通过 fetch 消费节点级 SSE。
- `mcp/server.py`：只读搜索、问答、来源 resource 与复用 prompt。

`/api/v1/chat/stream` 输出的是 LangGraph 节点完成事件，不是 token-by-token 模型流。

## 6. 评测和质量门禁

- `evaluation/metrics.py`：Recall@K、MRR、nDCG。
- `scripts/eval_retrieval.py`：版本化 JSONL、延迟统计、JSON/Markdown 报告。
- `tests/`：纯离线单元测试，不下载模型、不访问真实 API。
- `.github/workflows/ci.yml`：Python 3.10/3.12、Ruff、覆盖率和 Docker build。

运行命令和评测边界见 [evaluation.md](evaluation.md)。
