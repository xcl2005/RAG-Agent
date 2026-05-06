# RAG 调优记录模板

这个文件用于面试时说明：你不是只会调用 API，而是知道如何定位 RAG 效果问题。

## 1. 先判断问题类型

| 问题现象 | 常见原因 | 优先排查 |
| --- | --- | --- |
| 完全检索不到 | 解析失败、chunk 太大/太小、embedding 模型不适合 | loader、chunk、topK |
| 检索到了但排前面的不对 | 向量召回噪声、关键词召回不足 | hybrid、RRF、rerank |
| 答案胡编 | context 不够、prompt 约束弱、证据门控过松 | evidence gate、引用校验 |
| 回答太慢 | topK 太大、reranker 太重、文档太多 | batch、缓存、异步导入 |

## 2. 推荐调参顺序

不要一开始就换大模型，先按这个顺序：

```text
文档解析是否正确
→ chunk_size / overlap
→ dense_top_k / sparse_top_k
→ fusion_top_k
→ rerank_top_k
→ min_relevance_score
→ prompt / LLM model
```

## 3. 起始参数

中文业务资料：

```env
CHUNK_SIZE=700
CHUNK_OVERLAP=120
DENSE_TOP_K=40
SPARSE_TOP_K=40
FUSION_TOP_K=20
RERANK_TOP_K=8
MIN_RELEVANCE_SCORE=0.01
```

论文、报告、制度文档：

```env
CHUNK_SIZE=1000
CHUNK_OVERLAP=180
DENSE_TOP_K=60
SPARSE_TOP_K=60
FUSION_TOP_K=30
RERANK_TOP_K=10
MIN_RELEVANCE_SCORE=0.01
```

## 4. 如何解释幻觉控制

面试里不要只说“Prompt 让模型不要胡说”。更好的说法是：

```text
我把幻觉控制拆成三层：
1. 检索层：混合检索 + rerank 尽量把正确证据召回。
2. 门控层：检索为空或相关性低时拒答。
3. 生成层：强制基于 context 回答，并返回来源引用，方便人工核查。
```

## 5. 评估方式

先做一个小型 JSONL：

```jsonl
{"question":"系统如何降低幻觉？","expected_keywords":["引用","证据","拒答"]}
{"question":"为什么要 rerank？","expected_keywords":["CrossEncoder","二次排序"]}
```

然后运行：

```bash
python scripts/eval_retrieval.py --file data/eval/sample_retrieval.jsonl
```

这不是严格学术评测，但足够说明你有工程化评估意识。
