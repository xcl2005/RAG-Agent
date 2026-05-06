
# 代码阅读顺序：从零看懂这个 RAG Agent 项目

这份文档按“程序真实执行顺序”解释代码。你不用一上来全看，按下面顺序看最容易懂。

---

## 1. 先看整体流程

项目分成两条主线：

```text
资料入库链路：
文件 -> 文本解析 -> chunk 切分 -> SQLite 关键词索引 + Qdrant 向量索引

用户问答链路：
问题 -> Query 改写 -> hybrid search -> RRF 融合 -> rerank -> 证据判断 -> LLM 回答
```

---

## 2. 资料入库链路

### 第一步：`scripts/ingest.py`

这是命令行入口：

```bash
python scripts/ingest.py --path data/raw --reset
```

它只做一件事：调用 `Indexer().ingest_path(...)`。

---

### 第二步：`src/rag_agent/ingest/indexer.py`

`Indexer` 是资料入库的总调度器。

它按顺序调用：

```text
load_documents()     # 读取 PDF/Word/Markdown/TXT/HTML
chunk_documents()    # 切 chunk
sqlite.upsert_chunks()  # 写关键词索引和原文
vector.upsert_chunks()  # 写向量索引
```

---

### 第三步：`src/rag_agent/ingest/loaders.py`

负责不同文件格式的解析。

你要记住：

```text
PDF：按页解析，metadata 里保留 page
DOCX：按段落解析
HTML：去掉 script/style/nav/footer
TXT/MD：直接读取文本
```

保留 `source`、`page`、`chunk_index` 是为了最终回答能引用来源。

---

### 第四步：`src/rag_agent/ingest/chunker.py`

这是 RAG 面试重点。

本项目不是简单硬切，而是递归切分：

```text
段落 -> 换行 -> 中文句号/感叹号/问号 -> 英文句号 -> 空格 -> 字符
```

然后加 overlap，避免上下文断裂。

---

## 3. 检索链路

### 第一步：`src/rag_agent/retrieval/vector_store.py`

负责 Qdrant 向量检索。

```text
chunk text -> embedding -> Qdrant
question -> embedding -> Qdrant search
```

向量检索擅长找“意思相近”的内容。

---

### 第二步：`src/rag_agent/retrieval/sqlite_store.py`

负责 SQLite FTS5 关键词检索。

关键词检索擅长找：

```text
专有名词、错误码、API 名称、精确术语
```

为了增强中文检索，代码里额外加入了中文 bigram。

---

### 第三步：`src/rag_agent/retrieval/hybrid.py`

这是混合检索总流程：

```text
dense search
+ sparse search
-> RRF fusion
-> get chunk text
-> rerank
```

面试时重点讲：

> 向量检索解决语义相似，关键词检索解决精确匹配，RRF 负责融合两路召回，reranker 做二阶段精排。

---

### 第四步：`src/rag_agent/retrieval/reranker.py`

CrossEncoder reranker 会同时看问题和 chunk，判断这段证据是否真的能回答问题。

它比单纯 embedding 相似度更慢，但更准，所以只对融合后的 top20 做 rerank。

---

## 4. Agent 链路

### 第一步：`src/rag_agent/agent/graph.py`

LangGraph 工作流：

```text
rewrite_query -> retrieve -> grade_evidence -> generate_answer
```

这就是本项目能叫 RAG Agent 的原因：它不是单纯固定拼 prompt，而是把检索、证据判断、回答生成拆成状态节点。

---

### 第二步：`src/rag_agent/agent/prompts.py`

这里控制幻觉：

```text
只能基于 CONTEXT 回答
关键结论必须引用 [S1]/[S2]
证据不足必须拒答
资料冲突要指出冲突
```

---

### 第三步：`src/rag_agent/llm/client.py`

封装大模型调用。使用 OpenAI-compatible 接口，所以可以换成 DeepSeek/Qwen/OpenAI 等。

---

## 5. API 链路

### `src/rag_agent/api/main.py`

FastAPI 提供接口：

```text
GET  /health
POST /ask
POST /ingest
POST /upload
GET  /sources
```

如果你以后加前端，前端主要调用 `/ask` 和 `/upload`。

---

## 6. 面试时怎么讲这个项目

可以这样说：

> 我做的是一个企业知识库 RAG Agent。资料导入时支持 PDF、Word、Markdown、TXT、HTML，会进行递归 chunk 切分和 overlap，然后分别写入 Qdrant 向量库和 SQLite FTS5 关键词索引。用户提问后，Agent 会先做 Query Rewrite，然后走向量检索和关键词检索，使用 RRF 融合结果，再用 CrossEncoder reranker 做二阶段精排。生成回答前有 evidence gate，如果证据不足就拒答，回答时强制引用来源，降低幻觉。

---

## 7. 最先要看懂的 5 个文件

```text
1. src/rag_agent/agent/graph.py          # Agent 工作流
2. src/rag_agent/retrieval/hybrid.py     # 混合检索
3. src/rag_agent/ingest/chunker.py       # chunk 切分
4. src/rag_agent/retrieval/sqlite_store.py # 关键词检索
5. src/rag_agent/retrieval/vector_store.py # 向量检索
```
