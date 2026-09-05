# Engineering Reference

> 这份文档是开发参考，不是第一学习入口。
>
> 如果你是第一次学项目，先读 [LEARNING_GUIDE.md](LEARNING_GUIDE.md)。

# 1. 系统边界

项目由三条主要能力组成：

```text
A. Ingestion
文件 → 解析 → chunk → SQLite/FTS + Qdrant

B. RAG workflow
问题 → query planning → hybrid retrieval → RRF → rerank
→ evidence gate → context selection → generation → citation validation

C. Tool runtime
问题 → structured tool decision → registry → schema validation
→ timeout/error boundary → tool execution → observation → bounded next step/final
```

C 是新增的独立 runtime，目前没有替换 B。

# 2. 代码地图

```text
src/rag_agent/
├── agent/
│   ├── graph.py          # 主 RAG LangGraph
│   ├── guardrails.py     # 输入/引用等边界
│   ├── prompts.py        # 上下文和 Prompt
│   └── tooling.py        # bounded Tool Agent runtime
├── api/
│   ├── main.py           # FastAPI / SSE / upload / jobs
│   ├── jobs.py           # 当前进程内 job registry
│   └── models.py         # HTTP contracts
├── evaluation/
│   ├── lab.py
│   └── metrics.py
├── ingest/
│   ├── loaders.py
│   ├── chunker.py
│   └── indexer.py
├── llm/
│   └── client.py
├── mcp/
│   └── server.py
├── retrieval/
│   ├── hybrid.py
│   ├── fusion.py
│   ├── reranker.py
│   ├── sqlite_store.py
│   └── vector_store.py
└── web/
```

# 3. Ingestion

## 3.1 Loader

职责：

- 按文件类型抽取文字
- 保留 source / page / heading 等 metadata
- 不把“文件成功打开”误认为“有可用文本”

扫描 PDF 可能 0 文本。

当前没有 OCR。

因此正确状态语义应该是：

```text
upload success
!=
text extracted
!=
chunks created
!=
index ready
```

## 3.2 Chunk

chunk 是检索的最小证据单位。

主要 trade-off：

块太小：

- 上下文断裂
- 条件丢失
- 召回到半句话

块太大：

- 噪声增加
- rerank 成本增加
- context 浪费

overlap：

优点：

- 减少边界截断

代价：

- 重复
- 索引增大
- context 去重压力

## 3.3 幂等索引

不能只用文件名判断是否重复。

项目使用：

- 文档身份
- 内容 hash
- index fingerprint
- chunk/vector cleanup

目标是：

```text
同一版本重复 ingest
→ 不制造重复数据
```

而不是：

```text
所有同名文件都永远跳过
```

# 4. SQLite 与 Qdrant

SQLite：

- 正文
- metadata
- manifest
- FTS5
- checkpoint 相关本地状态

Qdrant：

- vector search

不能把两者说成“一个事务”。

典型更新：

```text
prepare new vectors
→ SQLite transaction update
→ cleanup old vectors
```

失败时需要补偿。

项目通过“回 SQLite 取权威正文”避免孤儿向量直接进入最终回答。

这不是严格 distributed transaction。

# 5. Hybrid Retrieval

文件：

`src/rag_agent/retrieval/hybrid.py`

流程：

```text
query variants
├─ dense
└─ sparse
   ↓
weighted RRF
   ↓
resolve chunks from SQLite
   ↓
rerank
```

## Dense

优势：

- semantic similarity
- paraphrase

弱点：

- exact ID / error code 可能不稳
- score 不是答案正确率

## Sparse

优势：

- 精确词
- 错误码
- API 名称

弱点：

- 同义词
- 跨语言
- 改写

## RRF

目的：

不同检索后端原始分数不同量纲。

因此先融合 rank：

```text
score(d) += weight / (k + rank)
```

RRF 分数是排序信号。

不是 confidence probability。

## Reranker

把：

```text
query + candidate
```

一起判断。

适合对少量候选更精细排序。

代价：

- latency
- compute
- model failure

所以：

```text
retrieve broad
→ rerank narrow
```

# 6. Evidence Gate

主图在生成前做证据门控。

当前使用：

- reranker normalized signal
- dense cosine
- sparse token coverage

ANY signal pass。

这样避免：

一个不稳定的 reranker 分数把明显 exact match 全部否掉。

代价：

OR gate 也可能放行主题相似但不够支持结论的文本。

所以最终仍需要更完整：

- answer support eval
- faithfulness eval

# 7. Context Engineering

context selection 要解决：

- duplicate
- source coverage
- char budget
- strong evidence placement
- quote 与模型实际所见一致

关键原则：

**模型没有看到的原文，不应该在 citation quote 里假装它看到了。**

当前还是字符预算。

未来：

- token-aware budget
- model-specific tokenizer
- dynamic compression

# 8. Citation

当前：

- `[S1]` 等编号
- 来源映射
- 格式/编号验证
- bounded repair

能证明：

```text
引用结构合法
```

不能证明：

```text
答案每一句都被来源语义支持
```

例如：

来源：

```text
timeout = 30
```

模型：

```text
timeout = 60 [S1]
```

编号可以合法，但结论仍错。

未来要做：

- claim extraction
- evidence support
- entailment / judge
- labeled eval

# 9. Main LangGraph

主图是 bounded workflow。

核心思想：

```text
model decision
+
deterministic control
```

不是无限 autonomous agent。

典型：

```text
initialize
→ plan
→ retrieve
→ grade
  ├─ retry bounded
  ├─ abstain
  └─ context
     → generate
     → citation validate
        ├─ repair once
        └─ finalize
```

为什么要 bounded：

- cost
- latency
- infinite loop
- debugging
- predictable failure

# 10. Tool Runtime

文件：

`src/rag_agent/agent/tooling.py`

目标：

补真实 Agent Backend 中最基础的 tool execution mechanics。

当前有：

## Tool Registry

只允许显式注册。

模型不能获得 Python callable。

## Schema

Pydantic validation。

作用：

```text
LLM JSON
→ local validation
→ handler
```

不是：

```text
LLM 生成什么参数
→ 直接执行
```

## Timeout

每个工具单独配置 timeout。

状态：

- ok
- unknown_tool
- invalid_arguments
- timeout
- execution_error

## Output boundary

工具返回：

- 序列化
- 最大字符
- truncation

未来还需要：

- MIME/type
- structured observation
- secret redaction
- per-tool permission

## Step limit

BoundedToolAgent 最大步骤有限。

防：

- infinite tool loop
- cost runaway

## Tool output = untrusted data

检索资料或外部 API 可能包含：

```text
ignore previous instructions
```

这些是数据，不是系统指令。

## Current tool

`search_knowledge_base`

复用：

`HybridRetriever`

只读。

目前没有：

- write tool
- risky tool
- HITL

所以安全边界相对简单。

# 11. MCP 与 Tool Runtime 区别

MCP：

**协议/互操作接口**

Tool Runtime：

**Agent 内部如何选择、验证、执行工具**

当前项目：

- MCP server：外部 Agent/IDE 可以调用知识库
- Tool Runtime：本项目模型可以通过独立 bounded runtime 调用注册工具

二者不能混成一个概念。

# 12. API

FastAPI：

- `/api/v1/chat`
- `/api/v1/chat/stream`
- `/api/v1/documents`
- `/api/v1/ingest`
- `/api/v1/jobs/{id}`
- `/api/v1/sources`

SSE：

当前发送 workflow events。

不是：

逐 token streaming。

为什么用 SSE：

- server → client
- 简单
- 浏览器原生思路
- 适合进度

如果未来需要：

双向实时控制

才考虑 WebSocket。

# 13. Background Job

当前 ingestion job registry：

**单进程内存状态。**

FastAPI BackgroundTasks：

**不是 durable queue。**

进程 crash：

任务可能丢。

服务 restart：

job status 可能丢。

因此当前准确描述：

```text
background ingestion
```

而不是：

```text
durable distributed task system
```

Roadmap：

```text
persistent job state
→ worker abstraction
→ lease
→ retry
→ cancellation
→ resume
→ queue
```

再考虑：

- Redis
- Postgres
- Celery/RQ/Arq
- Kafka

不要反过来先装 MQ。

# 14. Async / Concurrency

async 适合：

I/O wait。

不会让：

CPU-heavy reranker

自动更快。

需要区分：

- async coroutine
- thread
- process
- GPU work
- external service

Agent 系统额外需要：

- overall deadline
- per-model timeout
- per-tool timeout
- cancellation propagation
- concurrency limit
- backpressure

当前 tool runtime 只实现 per-tool timeout。

# 15. Security

当前已有：

- API access key
- admin key
- allowed ingest root
- upload limit
- file suffix/magic checks
- prompt injection basic handling
- MCP read-only
- tool registry allowlist
- tool arg validation
- tool output untrusted rule

未完成：

- OAuth
- JWT
- RBAC
- ABAC
- tenant isolation
- per-tool permission
- sandbox
- high-risk action confirmation
- audit trail
- secret broker

# 16. Observability

当前：

- trace_id
- node latency
- queries
- retrieval debug
- LLM usage
- tool execution step/status/latency

未来：

- structured event schema
- OpenTelemetry
- span hierarchy
- metric backend
- log aggregation
- replay
- alert
- dashboard

# 17. Failure Taxonomy

至少区分：

## RAG

- insufficient_evidence
- generation_failure
- citation_failure

## Tool Runtime

- unknown_tool
- invalid_arguments
- timeout
- execution_error
- model_failure
- empty_final_answer
- tool_step_limit

失败分类本身就是 Agent Backend 重要能力。

否则 UI 只会显示：

```text
Something went wrong
```

无法调试。

# 18. Docker / CI

Docker 解决：

环境可重复。

不自动解决：

- HA
- autoscaling
- durable state

CI 当前检查：

- Ruff
- mypy
- pytest
- coverage
- offline retrieval experiment
- frontend helper test

绿色 CI：

只证明这些检查通过。

不证明：

- real-model quality
- production load
- security
- latency SLA

# 19. 当前工程边界

不能写：

- production-grade multi-tenant
- zero hallucination
- exactly-once
- distributed transaction
- durable agent
- full Agent Runtime
- calibrated confidence

可以写：

- production-minded
- bounded
- explicit failure states
- testable
- observable locally
- hybrid RAG
- tool runtime demo
- offline evaluation

# 20. 推荐代码阅读顺序

```text
schemas.py
→ ingest/loaders.py
→ ingest/chunker.py
→ retrieval/sqlite_store.py
→ retrieval/vector_store.py
→ retrieval/hybrid.py
→ retrieval/fusion.py
→ retrieval/reranker.py
→ agent/prompts.py
→ agent/guardrails.py
→ agent/graph.py
→ llm/client.py
→ api/main.py
→ mcp/server.py
→ agent/tooling.py
→ evaluation/
```

每读一个文件都回答：

1. 输入是什么？
2. 输出是什么？
3. 谁调用？
4. 失败是什么？
5. 为什么不用更简单方法？
6. 测试在哪里？
7. 以后怎么扩？
