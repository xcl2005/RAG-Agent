# 评测与回归方法

这套项目把“代码正确”和“RAG 效果好”分开验证：

- 单元测试验证状态转移、引用规则、检索融合、幂等入库和 API 合同。
- 离线检索评测验证相关文档是否被召回以及排序位置。
- `should_answer` 标签验证证据门控的误拒答和错误放行。
- 生成质量与语义引用仍需要扩展后的人工标注集，不能从单元测试覆盖率推断。

## 1. 单元测试

```powershell
.\.venv\Scripts\pytest --cov=rag_agent --cov-report=term-missing
```

`pyproject.toml` 将总覆盖率门槛设为 75%。重点测试包括：

- 弱证据有界重试、充分证据回答、缺失引用修复和多轮 `thread_id`。
- Dense/Sparse 部分不可用时的检索降级和加权 RRF。
- reranker 显式 score mode 与批次无关的 `[0, 1]` 数值归一化。
- 文档 Prompt Injection 标签、上下文转义和引用编号越界。
- 文档哈希幂等、Qdrant 写失败、逐文件失败隔离和旧向量清理。
- FastAPI 依赖解析、共享密钥鉴权和核心路由 smoke。

覆盖率只表示代码路径被执行，不表示检索准确率或答案忠实度。

## 2. 检索数据集

每行一个 JSON 对象：

```json
{
  "id": "hybrid-001",
  "question": "为什么还需要关键词检索？",
  "relevant_sources": ["retrieval-guide.md"],
  "expected_keywords": ["错误码", "精确匹配"],
  "should_answer": true,
  "tags": ["hybrid", "exact-term"]
}
```

字段约定：

| 字段 | 说明 |
|---|---|
| `id` | 跨版本稳定的用例 ID |
| `question` | 用户实际可能提出的问题 |
| `relevant_sources` | 人工判断的相关来源文件名，优先作为检索真值 |
| `expected_keywords` | 小型示例集的后备判断；正式评测不要只靠关键词 |
| `should_answer` | 是否应当回答，为后续拒答指标预留 |
| `tags` | 语义改写、精确术语、多跳、不可回答、恶意文档等分组 |

`data/eval/sample_retrieval.jsonl` 只有格式演示价值。正式简历实验建议：

- 使用 8–12 份可公开或虚构的企业文档。
- 标注 50–80 道问题。
- 至少覆盖语义改写、错误码/编号、多文档、版本冲突、不可回答和 Prompt Injection。
- 将数据集版本、标注规则和 Git commit 一起写入报告。

## 3. 运行检索评测

先启动 Qdrant并完成入库：

```powershell
docker compose up -d qdrant
.\.venv\Scripts\python scripts/ingest.py --path data/raw
.\.venv\Scripts\python scripts/eval_retrieval.py `
  --file data/eval/sample_retrieval.jsonl `
  --output-dir reports
```

输出：

- `reports/retrieval-eval.json`：适合程序比较和保存原始记录。
- `reports/retrieval-eval.md`：适合代码评审或项目展示。

当前脚本报告：

- `Recall@5/10`：前 K 个结果覆盖了多少人工相关来源。
- `MRR`：第一个相关结果出现位置的倒数均值。
- `nDCG@5/10`：相关结果是否被排在更靠前的位置。
- `false_refusal_rate`：有答案的问题被证据门控拒绝的比例。
- `false_answer_rate`：无答案的问题被证据门控放行的比例。
- 回答与拒答各自的 Precision/Recall，以及 TP/TN/FP/FN 原始计数。
- 检索 mean、p50、p95 延迟。

这里评估的是“检索结果能否通过证据门控”，并不等同于最终答案正确。
每条报告会同时保留三路分数、阈值与门控原因，便于复盘是 reranker、dense 还是 sparse
信号导致了决策。

## 4. 消融实验

不要只运行“最终配置”。保持数据、硬件和模型不变，至少比较：

| 实验 | 用途 |
|---|---|
| Sparse only | 精确词、编号和错误码 baseline |
| Dense only | 语义相似 baseline |
| Dense + Sparse + RRF | 验证混合召回收益 |
| Hybrid + reranker | 验证二阶段排序收益 |
| Hybrid + reranker + query planning | 验证多查询是否值得额外模型调用 |

每次实验保存完整环境：

```text
git_sha
dataset_version
embedding_model
reranker_model
chunk_size / overlap
dense/sparse/fusion/rerank top-k
RRF k and weights
CPU/GPU/RAM
warmup and repetition count
```

只有使用同一评测集、硬件和判断规则的结果才能直接比较。

## 5. 已自动化与尚未自动化的边界

当前仓库已经用 `should_answer` 自动评估证据门控，但没有声称已经自动完成以下评测：

- 答案正确性和 claim-level faithfulness。
- 引用内容是否在语义上支持对应结论。
- 引用 Precision/Recall 与覆盖率。
- 并发吞吐、端到端 TTFT 和真实 token 成本回归。

下一阶段应先人工标注 claim-to-evidence 对，再评估是否加入经过校准的 LLM judge。

## 6. 简历数字的最低证据要求

任何“提升 X%”至少需要同时保留：

1. baseline 与新配置。
2. 固定版本的数据集和样本数。
3. 可复现命令与原始 JSON 报告。
4. 相同硬件、预热和重复次数。
5. 失败案例，而不只是平均数。

没有这些证据时，正确表述是“建设了 Recall/MRR/nDCG 离线评测与回归基础”，
不是“准确率提升了 30%”。
