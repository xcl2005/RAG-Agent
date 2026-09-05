# Evaluation and Experiments

> 评测的目的不是给 README 制造漂亮数字，而是回答：
>
> **改动到底有没有变好，坏在哪里，代价是什么。**

# 1. 四层评测

## Layer 1：Unit Test

测代码合同。

例如：

- chunk overlap
- RRF
- citation parsing
- context budget
- Tool Registry
- Tool argument validation
- timeout classification

Unit test 通过：

不代表 Agent 回答正确。

---

## Layer 2：Retrieval Eval

测：

- Recall@K
- MRR
- nDCG
- source coverage

问题：

```text
正确来源有没有找回来？
排第几？
```

---

## Layer 3：Gate / Routing Eval

测：

- false reject
- false allow

例如：

有答案却拒答：

```text
false rejection
```

没有答案却放行：

```text
false acceptance
```

降低拒答率时必须同时看错误放行。

---

## Layer 4：End-to-End Agent Eval

最终需要测：

- answer correctness
- groundedness
- citation support
- task success
- tool selection
- argument validity
- tool result use
- recovery
- step count
- latency
- token
- cost

当前这一层仍不完整。

---

# 2. 当前离线 Portfolio Eval

数据：

`data/eval/portfolio/`

包含公开虚构工程语料。

脚本：

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py
```

目的：

- 离线
- 无 Key
- 无私人资料
- 可重复

当前主要能证明：

检索和门控逻辑可以用固定数据回归。

不能证明：

真实企业数据准确率。

---

# 3. 指标

## Recall@K

```text
top K 找到的 relevant
/
全部 relevant
```

如果需要两份来源：

只找到一份：

Recall = 0.5

## MRR

看：

第一个相关结果的位置。

rank = 1：

1

rank = 2：

0.5

MRR 不告诉你所有相关来源是否都找全。

## nDCG

更关心：

相关结果是否排在前面。

适合多相关文档。

---

# 4. 门控指标

## False Reject Rate

可回答题被拒答。

## False Allow Rate

不可回答题被放行。

这两个需要一起看。

不能：

```text
threshold ↓
→ refusal ↓
→ 宣布更好
```

因为可能：

```text
wrong answer ↑
```

---

# 5. Reranker Ablation

未来标准实验：

```text
A dense only
B sparse only
C dense+sparse
D dense+sparse+RRF
E dense+sparse+RRF+rerank
```

保持：

- dataset
- query
- top_k
- threshold

尽量单变量。

记录：

- Recall
- MRR
- nDCG
- latency
- memory/model load

回答：

**rerank 到底提升了什么？**

---

# 6. Query Rewrite Ablation

比较：

```text
original only
vs
original + deterministic variants
vs
original + LLM variants
```

看：

- recall gain
- query drift
- latency
- token
- false allow

---

# 7. Context Eval

要测：

- evidence kept
- source diversity
- answer-containing span 是否被截掉
- total token
- duplicate
- conflict

当前项目有字符预算。

未来改 token-aware 后需要回归：

同样数据：

是否改变答案？

---

# 8. Citation Eval

当前 validation：

结构层。

未来至少分：

## Citation validity

编号存在。

## Citation correctness

引用来源真的支持附近结论。

## Citation completeness

需要证据的结论是否都有引用。

## Citation precision

引用是不是无关来源。

---

# 9. Tool Runtime Eval

新增 `tests/test_tooling.py` 先测 deterministic contract：

- unknown tool
- invalid args
- timeout
- successful tool
- bounded step limit

下一步要增加 dataset：

每题标注：

```json
{
  "question": "...",
  "expected_tool": "search_knowledge_base",
  "expected_argument_contains": "...",
  "should_finish": true
}
```

指标：

- tool selection accuracy
- argument validity rate
- execution success rate
- recovery success
- average steps
- p50 / p95 latency
- model token

---

# 10. Agent Task Success

最终最重要。

例如任务：

```text
根据知识库找到 API 超时并解释失败重试规则
```

成功条件不能只是：

调用了 search tool。

而要：

- 选对工具
- 参数合理
- 找到正确资料
- 最终回答正确
- 不执行多余高风险动作
- 步数不超限

这才是：

Task Success。

---

# 11. Failure Taxonomy

每次 eval 保存失败原因。

建议：

```text
retrieval_miss
ranking_error
gate_false_reject
gate_false_allow
context_truncation
generation_empty
generation_wrong
citation_invalid
citation_unsupported
tool_unknown
tool_invalid_args
tool_timeout
tool_error
tool_loop_limit
permission_denied
model_failure
```

不要只保存：

failed=true。

---

# 12. Latency

至少记录：

- retrieval
- rerank
- LLM
- tool
- total

以后：

- p50
- p95
- p99

本地作品集先 p50/p95 即可。

---

# 13. Cost

模型 API：

```text
input token
output token
```

工具：

可能有 API cost。

未来 eval 报告记录：

```text
avg input tokens
avg output tokens
avg model calls
avg tool calls
estimated cost
```

没有价格配置时：

不要编造人民币/美元成本。

---

# 14. Regression

任何重要修复都要加入：

最小复现 case。

例如：

- context quote 截断错位
- empty model output
- unknown tool
- timeout

这样 bug 不会下次升级又回来。

---

# 15. Development Set 与 Test Set

开发时不停调 threshold：

数据已经被“看过”。

所以它是：

development set。

要证明泛化：

冻结 holdout。

不要调它。

---

# 16. 真实模型 Eval

离线 FakeLLM：

优点：

- 快
- 稳
- 免费

缺点：

不代表真实模型。

真实 eval 必须明确：

- provider
- model
- date
- prompt version
- dataset hash
- settings
- random/reasoning controls

否则结果无法复现。

---

# 17. 推荐下一批实验

## P0

1. Dense/Sparse/Hybrid/Rerank ablation
2. Tool selection dataset
3. final answer + citation support
4. threshold false-allow trade-off
5. latency report

## P1

6. token-aware context
7. retry/fallback
8. real-model regression
9. cost

## P2

10. concurrency/load
11. multi-agent
12. production telemetry

---

# 18. 运行测试

```powershell
.\.venv\Scripts\python -m pytest -m "not integration" -q
```

覆盖率：

```powershell
.\.venv\Scripts\python -m pytest -m "not integration" --cov=rag_agent
```

静态检查：

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
```

前端 helper：

```powershell
node --test tests/web_ui_helpers.test.cjs
```

---

# 19. 结果写法

好：

> 在 32 题公开虚构开发集上比较 sparse baseline 和固定 query expansion，并同时记录 MRR、误拒答和错误放行。

不好：

> RAG 准确率提升 30%。

除非：

你真的定义、计算并保存了这个准确率。

---

# 20. 求职表达

面试官问：

“怎么证明你的 Agent 变好了？”

回答结构：

```text
先定义任务成功
→ 固定数据
→ 单变量对照
→ 同时看正负指标
→ 记录失败 case
→ 加 regression
→ 再看 latency/cost
```

这比：

“我用了更强模型”

更像真实 AI Application Engineering。
