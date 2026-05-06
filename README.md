# Mainstream RAG Agent：大批量资料检索问答系统

这是一个适合写进简历、面试能讲清楚、同时难度不过分高的 **RAG Agent 项目**。它围绕“企业知识库问答 / 大批量资料检索 / 幻觉控制 / rerank / chunk 调优”来设计。

项目特点：

- 支持导入 `PDF / Word / Markdown / TXT / HTML` 资料。
- 使用 **Qdrant 向量库** 做语义检索。
- 使用 **SQLite FTS5** 做关键词检索，并加入中文 bigram 辅助索引。
- 使用 **RRF** 做 dense + sparse 混合召回融合。
- 使用 **CrossEncoder reranker** 对候选片段二次排序。
- 使用 **LangGraph** 编排 Agent 流程：问题改写 → 检索 → 证据判断 → 回答生成。
- 使用 **FastAPI** 提供问答 API。
- 提供 chunk size、overlap、topK、rerank topK、幻觉阈值等可调参数。
- 回答必须带引用来源，证据不足时拒答，降低幻觉。
- **代码已加入大量中文注释**，适合边跑边学。
- 新增 `docs/code_walkthrough.md`，按程序执行顺序讲解每个核心文件。

> 这个项目不是“堆技术名词”，而是一个简化版真实企业 RAG 系统。你可以把它包装为：企业内部文档知识库智能问答 Agent。

---

## 1. 技术栈选择

### 后端与 Agent 编排

- Python 3.10+
- FastAPI：提供 HTTP API。
- LangGraph：编排多步骤 Agent 工作流。
- OpenAI SDK：兼容 OpenAI / DeepSeek / 通义千问等 OpenAI-compatible API。

### 检索与向量库

- Qdrant：向量检索数据库。
- SentenceTransformers：本地 embedding。
- SQLite FTS5：关键词检索。
- RRF：融合向量检索和关键词检索结果。
- CrossEncoder：rerank，提高最终召回质量。

### 文档处理

- pypdf：PDF 文本抽取。
- python-docx：Word 文档抽取。
- BeautifulSoup：HTML 清洗。

---

## 2. 项目结构

```text
rag-agent-mainstream/
├── README.md
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── data/
│   ├── raw/
│   │   └── sample.md
│   └── eval/
│       └── sample_retrieval.jsonl
├── storage/
│   └── .gitkeep
├── scripts/
│   ├── ingest.py
│   ├── query.py
│   └── eval_retrieval.py
├── src/
│   └── rag_agent/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       ├── api/
│       │   └── main.py
│       ├── agent/
│       │   ├── graph.py
│       │   └── prompts.py
│       ├── ingest/
│       │   ├── chunker.py
│       │   ├── indexer.py
│       │   └── loaders.py
│       ├── llm/
│       │   └── client.py
│       ├── retrieval/
│       │   ├── hybrid.py
│       │   ├── reranker.py
│       │   ├── sqlite_store.py
│       │   └── vector_store.py
│       └── utils/
│           └── logging.py
├── docs/
│   ├── design.md
│   ├── tuning.md
│   ├── code_walkthrough.md
│   └── interview.md
└── tests/
    ├── test_chunker.py
    └── test_rrf.py
```

---

## 2.1 如果你是第一次看代码，建议按这个顺序

我已经在核心代码里加了中文注释。不要从 README 一口气看到底，建议先看：

```text
1. docs/code_walkthrough.md              # 从整体执行流程看懂项目
2. src/rag_agent/agent/graph.py          # Agent 工作流
3. src/rag_agent/retrieval/hybrid.py     # 混合检索：向量 + 关键词 + RRF + rerank
4. src/rag_agent/ingest/chunker.py       # chunk 切分和 overlap
5. src/rag_agent/api/main.py             # FastAPI 接口入口
```

你面试时最应该讲清楚的是：**为什么要切 chunk、为什么要 hybrid search、为什么要 rerank、怎么降低幻觉**。

---

## 3. 快速启动

### 3.1 创建环境

```bash
conda create -n rag-agent python=3.10 -y
conda activate rag-agent
pip install -r requirements.txt
```

Windows PowerShell 也一样：

```powershell
conda create -n rag-agent python=3.10 -y
conda activate rag-agent
pip install -r requirements.txt
```

### 3.2 启动 Qdrant

需要先安装 Docker Desktop。

```bash
docker compose up -d
```

检查：

```bash
docker ps
```

如果看到 `qdrant/qdrant` 正在运行即可。

### 3.3 配置大模型 API

复制环境变量文件：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
copy .env.example .env
```

然后修改 `.env`：

```env
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=gpt-4o-mini
```

如果使用 DeepSeek，可以写成：

```env
OPENAI_API_KEY=你的deepseek key
OPENAI_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-chat
```

如果使用通义千问兼容接口，根据你自己的平台文档填写 base url 和模型名。

---

## 4. 导入资料

把你的资料放到：

```text
data/raw/
```

支持：

- `.pdf`
- `.docx`
- `.md`
- `.txt`
- `.html`

执行索引：

```bash
python scripts/ingest.py --path data/raw --reset
```

参数说明：

- `--path`：资料目录。
- `--reset`：清空旧索引后重新导入。

---

## 5. 命令行问答

```bash
python scripts/query.py "这个系统如何降低幻觉？"
```

示例输出：

```text
回答：
本系统主要通过三层机制降低幻觉：第一，回答生成阶段只允许模型基于检索上下文作答；第二，所有关键结论必须带来源引用；第三，当检索结果为空或相关性低于阈值时，系统会拒答并提示证据不足。 [S1] [S2]

来源：
[S1] data/raw/sample.md
[S2] data/raw/sample.md
```

---

## 6. 启动 API 服务

```bash
uvicorn rag_agent.api.main:app --reload --app-dir src
```

打开：

```text
http://127.0.0.1:8000/docs
```

问答请求示例：

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"RAG 系统如何处理大批量资料检索？"}'
```

Windows PowerShell：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"RAG 系统如何处理大批量资料检索？"}'
```

上传并导入文件：

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "files=@data/raw/sample.md" \
  -F "reset=false"
```

这个接口会把文件保存到 `data/raw/uploads/`，然后立即执行索引导入。

---

## 7. 核心流程

用户问题进入系统后：

```text
用户问题
  ↓
Query Rewrite：问题改写，补全检索关键词
  ↓
Dense Search：Qdrant 向量召回
  ↓
Sparse Search：SQLite FTS5 关键词召回
  ↓
RRF Fusion：混合召回融合
  ↓
CrossEncoder Rerank：二次排序
  ↓
Evidence Gate：判断证据是否足够
  ↓
Answer Generation：基于上下文生成带引用回答
```

---

## 8. 为什么这样设计？

### 8.1 为什么不用纯 LangChain 一把梭？

因为面试时只会用封装不够。这个项目把核心模块拆开：

- loader
- chunker
- vector store
- sparse store
- hybrid retriever
- reranker
- graph agent
- API

这样你能讲清楚每一层做了什么。

### 8.2 为什么选择 Qdrant？

Qdrant 本地 Docker 就能跑，API 简单，适合展示向量数据库能力。相比直接用 Chroma，它更像生产环境组件。

### 8.3 为什么还要 SQLite FTS5？

只做向量检索容易漏掉精确名词、编号、错误码、政策条款。关键词检索对精确匹配更强。所以这里使用 hybrid retrieval。

### 8.4 为什么要 rerank？

向量库第一阶段追求快，召回的结果可能相关但不准确。CrossEncoder 会把“问题 + 候选片段”一起输入模型重新打分，通常能提升最终排序质量。

---

## 9. Chunk 调优建议

在 `.env` 中调整：

```env
CHUNK_SIZE=900
CHUNK_OVERLAP=150
DENSE_TOP_K=40
SPARSE_TOP_K=40
FUSION_TOP_K=20
RERANK_TOP_K=8
MIN_RELEVANCE_SCORE=0.01
```

### 9.1 chunk 太小的问题

优点：召回更精准。

缺点：上下文不完整，模型容易缺少前因后果。

适合：FAQ、短条款、接口文档。

### 9.2 chunk 太大的问题

优点：上下文完整。

缺点：噪声多，embedding 表达不够精确，rerank 成本更高。

适合：长报告、教材、业务说明。

### 9.3 推荐起点

中文资料：

```env
CHUNK_SIZE=700
CHUNK_OVERLAP=120
```

英文技术文档：

```env
CHUNK_SIZE=900
CHUNK_OVERLAP=150
```

论文 / 报告：

```env
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
```

---

## 10. 幻觉处理策略

本项目不是简单要求模型“不要胡说”，而是做了工程约束：

1. **只基于上下文回答**：prompt 明确要求不使用外部知识补全。
2. **引用强制**：关键结论必须带 `[S1]`、`[S2]` 来源。
3. **证据门控**：检索为空或相关性低时拒答。
4. **低温度生成**：temperature 默认 0.1。
5. **展示来源**：API 返回 sources，方便人工核查。

注意：`MIN_RELEVANCE_SCORE` 不是固定真理。RRF 分数通常很小，reranker 分数又和模型有关，所以项目默认先设低一点，再用 `scripts/eval_retrieval.py` 根据自己的资料集调优。

---

## 11. 检索评估

准备一个 JSONL 文件，例如：

```jsonl
{"question":"系统如何降低幻觉？","expected_keywords":["证据","引用","拒答"]}
{"question":"为什么要 rerank？","expected_keywords":["CrossEncoder","二次排序"]}
```

运行：

```bash
python scripts/eval_retrieval.py --file eval.jsonl
```

它会检查 topK 结果中是否包含预期关键词，帮助你粗略评估不同 chunk 参数的影响。

---

## 12. 简历写法

可以写成：

> 基于 FastAPI + LangGraph + Qdrant 实现企业知识库 RAG Agent，支持 PDF/Word/Markdown 等多格式资料导入；设计递归 chunk 切分与 overlap 策略，结合 Qdrant 向量召回、SQLite FTS5 关键词召回、RRF 融合和 CrossEncoder rerank 提升大批量文档检索质量；通过证据门控、来源引用和低温度生成降低幻觉，并提供 RESTful API 与检索评估脚本。

更朴素一点：

> 参与实现企业文档智能问答系统，完成文档解析、切片、向量化、混合检索、rerank 与问答接口开发，理解 RAG 系统从资料入库到答案生成的完整流程。

---

## 13. 面试重点

面试官最可能问：

1. 为什么不能直接把所有资料塞给大模型？
2. RAG 的流程是什么？
3. chunk size 和 overlap 怎么选？
4. 向量检索和关键词检索有什么区别？
5. rerank 为什么有效？
6. 怎么判断回答是不是幻觉？
7. 如果资料越来越多，系统瓶颈在哪里？
8. 如果检索不到答案怎么办？
9. 你这个 Agent 和普通 RAG 有什么区别？
10. 你实际写了哪部分？

答案见 `docs/interview.md`。

---

## 14. 可扩展方向

后续可以继续加：

- 用户登录和权限控制。
- 文件上传 API。当前版本已支持 `/upload`，后续可加异步导入进度。
- 多租户知识库。
- Redis 缓存热门问题。
- Celery 异步导入大文件。
- MinIO 存储原始文件。
- PostgreSQL + pgvector 替换 Qdrant。
- LangSmith / OpenTelemetry 做 tracing。
- 前端 Vue3 管理页面。

对银行科技岗或 Java 后端面试来说，不需要一开始全做完。你先把当前版本跑通，并能讲清楚检索、rerank、幻觉处理，就已经很够用了。
