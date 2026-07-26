# 检索与工作流调优

调参必须围绕固定评测集进行；不能因为某几个演示问题“看起来更好”就修改默认值。

## 1. 推荐顺序

1. 固定文档、问题、相关来源标注和 embedding/reranker。
2. 先调 chunk，再调单路召回 top-k。
3. 比较 sparse-only、dense-only 与 hybrid。
4. 调 RRF 权重与 `rrf_k`。
5. 加 reranker 并在标注集上校准它的门槛。
6. 最后评估 query planning 是否值得额外调用和延迟。

每次实验只改一组相关变量，保存 `reports/retrieval-eval.json`。

## 2. Chunk

| 参数 | 太小 | 太大 |
|---|---|---|
| `CHUNK_SIZE` | 语义不完整、召回碎片化 | 噪声增加、重排和上下文成本升高 |
| `CHUNK_OVERLAP` | 跨边界事实可能断开 | 重复候选增多、索引膨胀 |

当前切片器保证最终 chunk 不超过 `CHUNK_SIZE`，Markdown 标题和 PDF 页码会进入 metadata。
如果主要资料是表格、扫描 PDF 或代码，应先升级解析和结构化切片，而不是盲目放大 chunk。

## 3. 召回与融合

| 配置 | 影响 |
|---|---|
| `DENSE_TOP_K` | 语义候选宽度 |
| `SPARSE_TOP_K` | 精确词候选宽度 |
| `DENSE_WEIGHT` / `SPARSE_WEIGHT` | 两路排名在 weighted RRF 中的贡献 |
| `RRF_K` | 越小越偏向排名头部，越大越平滑 |
| `FUSION_TOP_K` | 进入回表和 reranker 的候选上限 |
| `RERANK_TOP_K` | 最终返回的候选上限 |

原始问题权重固定高于模型生成的变体，避免错误码和专有名词被改写覆盖。
不要直接比较 Qdrant cosine、FTS ranking 和 CrossEncoder logit。

## 4. Evidence gate

- `MIN_RERANK_RELEVANCE` 用于显式 score mode 归一化后的 reranker 信号。
- `MIN_DENSE_RELEVANCE` 用于 Qdrant dense cosine。
- `MIN_SPARSE_COVERAGE` 用于查询 token 在候选文本中的覆盖率。

RRF 只融合排名，不能作为绝对相关性门槛；单个非空后端的 top-1 RRF 归一化值可能恒为 1。

阈值太低会让弱证据进入生成，太高会增加误拒答。正式调优需要同时报告：

- 可回答问题的回答率。
- 不可回答问题的拒答 Precision/Recall。
- Recall@K、MRR、nDCG。
- 平均检索尝试次数和延迟。

`confidence` 当前是最佳检索相关性信号，不是答案正确概率。

## 5. Agent 预算

| 参数 | 默认 | 约束 |
|---|---:|---|
| `MAX_RETRIEVAL_ATTEMPTS` | 2 | 1–4 |
| `MAX_QUERY_VARIANTS` | 3 | 1–6 |
| 引用修复次数 | 1 | 代码硬上限 |
| SDK timeout | 60 秒 | 代码配置 |
| SDK retry | 2 | 代码配置 |

增加重试或查询数可能提高召回，也会线性放大 dense/FTS 请求、模型调用和延迟。
先按 tag 分析失败问题；如果弱点是解析、文档版本或标注错误，增加 Agent 循环没有帮助。

## 6. 模型变更

更换 embedding 后必须使用新的 `QDRANT_COLLECTION` 或全量重建。代码会拒绝维度不一致，
但无法识别“维度相同、向量空间不同”的模型混用。

更换 reranker 后应重新校准 `MIN_RERANK_RELEVANCE`；固定 sigmoid 只提供稳定范围，
不会自动让不同模型具有相同概率意义。

完整运行方法见 [evaluation.md](evaluation.md)。
