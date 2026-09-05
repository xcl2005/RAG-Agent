# RAG Agent 简历与面试指南

## 1. 使用原则

你目前能写基础 Python、还讲不清项目，建议先完成 [14 天学习路线](learning-path.md) 的 A/B/E 实验。
本页是可取用的表达材料，不是你已完成全部工作的证明。AI 辅助实现、已有开源基础、你亲自验证和改动的部分要分开。
不要伪造“独立原创”、工作经历或提交历史；也不必为了显得像自己写的而故意降低代码质量。

这份指南用于把当前仓库中已经实现、可以通过代码或命令验证的能力写进简历。推荐遵循三条规则：

1. 只描述自己能够解释并现场演示的实现。
2. 性能和质量数字必须来自保存下来的报告，不能根据感觉填写。
3. 明确区分“作品集级生产意识”和“真实生产大规模落地”。

本项目适合描述为：

> 面向企业知识库场景的工程实践型 Adaptive RAG Agent。

不适合描述为：

> 已支撑百万用户、高并发、多租户生产环境的企业级平台。

## 2. 可核验项目描述

### 2.1 一句话版本

> 基于 FastAPI、LangGraph、Qdrant 与 SQLite FTS5 构建自适应企业知识库 RAG Agent，实现多查询混合检索、加权 RRF、可选 CrossEncoder 重排、证据门控、有限检索重试、服务端引用校验和持久化多轮状态，并提供 Web 演示界面与只读 MCP 接口。

### 2.2 简历三条版本

以下三条是仓库能力清单，只选择自己能解释、实际参与的部分。尚未自己复现评测时不要填写效果数字。

> **Adaptive RAG Agent｜Python / FastAPI / LangGraph / Qdrant / SQLite / MCP**
>
> - 设计有界 LangGraph 工作流，将查询规划、混合检索、证据门控、答案生成、引用校验和拒答拆分为可测试节点；保留原始问题并限制检索重试次数，证据不足或引用修复失败时主动拒答。
> - 实现 Qdrant dense retrieval 与 SQLite FTS5 中英文关键词检索，通过多查询加权 RRF 融合和可选 CrossEncoder rerank 提升候选排序；明确 RRF 只负责排序，证据门控分别使用 reranker、dense cosine 或 sparse token coverage。
> - 实现基于内容哈希的幂等入库和双存储更新顺序，使用 SQLite 事务原子替换文档清单、chunk 与 FTS，并通过 SQLite 权威回表屏蔽 Qdrant 孤儿/过期向量；提供安全上传、后台任务状态、节点级 SSE、静态 Web UI、离线 IR 指标与只读 MCP 能力。

如果版面允许，可增加：

> - 使用 SQLite LangGraph checkpointer 保存 `thread_id` 状态；记录节点耗时、模型 token usage、检索后端错误和引用校验结果，便于定位 RAG 质量与延迟问题。

### 2.3 更保守的中文项目介绍

> 完成一个企业文档问答系统的端到端工程实现，覆盖 PDF、DOCX、Markdown、TXT、HTML 解析、结构感知切分、向量化、关键词索引、混合召回、重排、证据回答和来源展示。项目重点不是堆叠多智能体，而是用有限状态图控制模型调用、失败降级和可验证输出。

该版本适合不希望在简历中突出“Agent”概念时使用。

### 2.4 亲手练习后的短版本

完成学习实验后，可以按真实情况改写为：

> 基于 Python / LangGraph 迭代文档问答作品，围绕上下文预算与拒答问题补充测试；
> 在隔离虚构语料上比较 FTS5 基线与查询扩展，记录检索排序、误拒答及错误放行，分析两个失败案例。

再补一句你具体改了哪个函数/测试。不要仅因仓库中存在模块，就声称每个模块都是你独立设计。

## 3. 每项说法如何核验

| 简历说法 | 代码证据 | 建议验证方式 |
|---|---|---|
| 自适应、有界 LangGraph | `src/rag_agent/agent/graph.py` | 查看 conditional edges；运行 `tests/test_agent_graph.py`。 |
| 持久化多轮状态 | `SqliteSaver`、`thread_id` | 使用相同 `thread_id` 连续提问，查看第二轮 trace 的 `history_turns`。 |
| 多查询混合检索 | `src/rag_agent/retrieval/hybrid.py` | 查看 `retrieve_many`；运行 `tests/test_hybrid.py`。 |
| 加权 RRF 与分数归一化 | `src/rag_agent/retrieval/fusion.py` | 运行 `tests/test_rrf.py`。 |
| 独立证据阈值 | `grade_evidence` 与 `Settings` | 检查 `min_rerank_relevance`、`min_dense_relevance`、`min_sparse_coverage`。 |
| 引用校验与一次修复 | `guardrails.py`、`graph.py` | 运行 `tests/test_guardrails.py` 和引用修复测试。 |
| 幂等入库 | `content_hash`、`document_is_current` | 同一文件连续导入两次，第二次应显示 `skipped`。 |
| 双存储一致性 | `ingest/indexer.py`、`sqlite_store.py` | 查看“Qdrant 先写、SQLite 事务替换、旧向量后删”的顺序。 |
| 安全上传 | `api/main.py` | 检查数量、大小、后缀、文件名、magic bytes 与根路径限制测试。 |
| Web UI | `src/rag_agent/web/` | 启动 API 后打开 `/`。 |
| MCP | `src/rag_agent/mcp/server.py` | 安装 `.[mcp]`，检查两个 tools、一个 resource 和一个 prompt。 |
| 离线评测 | `evaluation/metrics.py`、`scripts/eval_retrieval.py` | 生成 `reports/retrieval-eval.json` 和 Markdown 报告。 |
| 隔离对照实验 | `evaluation/lab.py`、`scripts/eval_portfolio.py` | 不用模型 Key / Docker，运行 8 文档 / 32 题并检查逐题结果。 |
| 上下文工程 | `prompts.py`、`graph.py::prepare_context` | 核对预算、同范围去重、来源覆盖与 quote 可见性测试。 |
| CI | `.github/workflows/ci.yml` | 查看 Python 版本矩阵、Ruff、pytest coverage 和 Docker build。 |

## 4. STAR 讲述框架

### 4.1 Situation：背景

可以这样说：

> 企业内部资料同时包含自然语言说明、错误码、接口名、政策编号和中英文混排内容。单纯向量检索可能漏掉精确术语，单纯关键词检索又难以覆盖同义表达；即使检索到资料，大模型仍可能生成没有合法来源的结论。原始版本还是固定的“改写—检索—回答”链路，缺少可恢复状态、有限重试和可量化评测。

避免说：

> 公司线上系统已经发生严重事故，所以我主导了生产改造。

除非这确实是你的真实经历。

### 4.2 Task：目标

> 我的目标是在不过度工程化的前提下，把项目升级为可现场演示、可测试、可解释的 Adaptive RAG：既能展示检索与 Agent 编排能力，又能诚实说明本地作品集的边界。

### 4.3 Action：行动

建议按四层讲：

1. **检索层**
   - 首轮保留原始问题，重试优先采用尚未尝试的变体。
   - 生成少量互补查询。
   - 对每个查询执行 Qdrant dense 与 SQLite FTS5。
   - 使用加权 RRF 融合排名，原问题权重更高。
   - CrossEncoder 可用时重排，加载失败时回退到 fusion ranking。

2. **工作流层**
   - 用 LangGraph conditional edges 控制“回答、重试、拒答”。
   - 默认最多两轮检索，引用最多修复一次。
   - 用 `thread_id` 和 SQLite checkpointer 保存多轮状态。

3. **可信与安全层**
   - 把检索文档视为不可信数据，转义后放入 evidence 容器。
   - 对文档中的 prompt injection 信号做标记。
   - 只返回真正进入模型上下文的 sources。
   - 服务端验证引用是否存在、是否越界；失败后修复一次，再失败就拒答。
   - 上传限制文件数、大小、后缀和二进制 magic bytes。

4. **工程与评测层**
   - 基于文件内容哈希跳过未变化文档。
   - 新向量先写 Qdrant，再用 SQLite 事务替换文本、FTS 和 manifest，最后清理旧向量。
   - 提供健康检查、后台导入任务、节点 trace、模型 usage、Web UI 和 MCP。
   - 实现 Recall、MRR、nDCG 和检索延迟报告。

### 4.4 Result：结果

没有正式基准数字时，使用可核验的功能结果：

> 升级后，系统能自动区分回答、有限重试和拒答路径；同一 `thread_id` 能读取历史；缺失或越界引用不会作为成功答案返回；重复导入未变化文件会跳过；dense 或 reranker 不可用时存在明确降级路径。以上核心路径都有离线单元测试。

有正式报告后，才补充数字：

> 在 `[数据集名称/版本]` 的 `[N]` 个检索问题上，`hybrid + rerank` 相比 `[baseline]` 将 Recall@5 从 `[A]` 提升到 `[B]`，MRR 从 `[C]` 提升到 `[D]`；在 `[硬件与并发]` 下检索 p95 为 `[X ms]`。

方括号内容必须由真实报告替换，不能原样放进简历。

## 5. 高频面试问答

### Q1：为什么叫 Agent，而不是普通 RAG？

**答：**

它不是完全自主的通用 Agent，而是有界 Agentic Workflow。模型只参与结构化查询规划、答案生成和一次引用修复；检索次数、状态转移、证据阈值、引用合法性和拒答由程序控制。与固定链相比，它会根据证据质量选择重试、回答或拒答，同时仍保留可预测的成本上限。

### Q2：为什么没有做多智能体？

**答：**

当前业务目标是一个知识库问答闭环，多智能体会增加路由误差、模型调用数和调试成本，却没有独立角色边界可以证明收益。LangGraph 中“确定性步骤 + 少量模型决策”更适合该场景。只有未来出现 SQL、外部搜索、审批等明显独立职责，并且评测证明 handoff 有收益时，才值得增加专门 Agent。

### Q3：为什么同时用 Qdrant 和 SQLite FTS5？

**答：**

Qdrant 解决语义相似问题，FTS5 更适合错误码、表名、编号等精确匹配。SQLite 还承担权威原文和文档清单，因此 dense 命中必须回 SQLite 解析。作品集规模下，这种组合容易本地部署，也能展示不同检索信号的取舍；更大规模时可根据评测替换关键词后端。

### Q4：为什么用 RRF，不直接相加分数？

**答：**

余弦相似度、BM25 和不同查询的分数尺度不一致，直接相加需要校准。RRF 只使用排名，更适合异构召回。
项目给原始问题更高权重，并将融合分数归一化用于排序和展示。RRF 不参与证据门控，不能把它的归一化说成门控概率校准。

### Q5：如何判断证据是否充分？

**答：**

分别检查 reranker 固定归一化分数、dense cosine 和 sparse token coverage，各自与独立阈值比较；
任一路通过即放行，是 OR 策略，不是 reranker 优先一票否决。RRF 只用于融合排名。
OR 减少单路误拒答，也可能增加错误放行，需要难负例验证。`confidence` 只是最佳门控信号，不是答案正确概率。

### Q6：引用校验能保证答案真实吗？

**答：**

不能。当前校验能保证实质性回答至少有引用，而且所有 `[S数字]` 都映射到模型实际看到的来源；它还会把无引用答案送去修复一次。它没有验证每个结论是否被对应来源语义支持，所以不能称为 claim-level factuality 或零幻觉。下一步可以增加 claim-to-evidence 标注集和语义评估器。

### Q7：如何处理文档中的 Prompt Injection？

**答：**

系统把检索内容定义为不可信数据，进行 HTML 转义并放入独立 evidence 容器。规则检测只产生 `security_flags`，不会随意删除合法内容；系统提示明确禁止执行文档内命令。这个方案降低风险，但不是完整沙箱，因为当前 RAG Agent 本身没有高危写工具。若以后加入外部操作工具，还需要工具级授权、参数校验和人工审批。

### Q8：SQLite 和 Qdrant 双写失败怎么办？

**答：**

先写新向量，再在 SQLite 单事务中替换该文档的 chunks、FTS 和 manifest，最后 best-effort 删除旧向量。如果 SQLite 提交失败，新向量可能成为孤儿，但 dense 结果必须回 SQLite 取原文，因此孤儿不会进入答案。如果旧向量删除失败，它同样无法回表解析。这个方案优先保证可见正确性，不声称两个存储存在分布式原子事务。

### Q9：为什么需要 checkpoint？

**答：**

`SqliteSaver` 让同一 `thread_id` 的 LangGraph 状态跨请求持久化，查询规划能参考最近对话，也为未来的中断恢复和人工审批提供基础。当前 API 已支持持久化多轮，但还没有线程管理或人工审批恢复端点，因此面试时不能把后者说成已完成。

### Q10：SSE 是模型 token 流吗？

**答：**

不是。当前 `/api/v1/chat/stream` 在每个 LangGraph 节点完成后发送一个 `node` 事件，
最后发送完整 `final` 事件。Web UI 会消费这些事件展示 workflow 进度，但尚未把
provider 的 token 增量传到前端。

### Q11：后台任务能否保证服务重启后继续？

**答：**

不能。当前使用 FastAPI `BackgroundTasks` 和线程安全的内存 `JobRegistry`，适合单进程演示。重启后任务状态会丢失，多 worker 也不共享状态。真实生产环境会保留 HTTP 的 `job_id/status` 合同，把实现替换为 Redis Queue、Dramatiq、Celery 或云任务队列。

### Q12：LLM 或向量库不可用时会怎样？

**答：**

- 查询规划失败：保留确定性查询变体，首轮含原问题，重试优先新变体。
- dense 失败：继续用 FTS5。
- FTS5 失败：dense 可用时继续。
- reranker 失败：按 fusion score 排序。
- LLM 未配置或生成失败：检索仍可执行，最终返回 `generation_failure` 技术错误，不伪装成证据不足。
- 两个检索后端都没有有效结果：有限重试后拒答。
- readiness 会把任一存储依赖失败报告为 503/degraded。

### Q13：MCP 在项目里解决什么问题？

**答：**

MCP 是跨宿主暴露知识库能力的协议边界，不替代 LangGraph 或检索。项目只读暴露 `search_knowledge_base`、`ask_knowledge_base`、来源 resource 和 grounded-research prompt，没有开放上传和 reset，避免外部 Agent 通过 MCP 修改索引。

### Q14：目前评测覆盖什么？

**答：**

已有 Recall、MRR、nDCG、延迟和基于 `should_answer` 的门控误拒答/错误放行及 Precision/Recall。
新增实验室用 8 份虚构文档 / 32 题比较 sparse 基线与术语扩展，保存数据哈希、参数和代码状态。
没有测量真实 GLM 的生成准确率，也没有自动化逐句 faithfulness 或独立保留集，不能说“完整解决了 RAG 评测”。

## 6. 可演示脚本

面试现场建议控制在 5–8 分钟。

不依赖服务的后备演示和 20 分钟模拟追问见 [面试演练](interview.md)。

### 6.1 启动与健康检查

```bash
docker compose up --build
```

打开：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
```

先展示 `/health/ready` 对 SQLite 和 Qdrant 的分别检查。

### 6.2 演示入库

1. 上传一个支持格式的文件。
2. 展示 API 立即返回 `job_id`。
3. 展示 UI 轮询 queued/running/succeeded。
4. 再次通过 CLI 对相同文件导入，说明内容哈希不变时会 `skipped`。

### 6.3 演示问答路径

至少准备三类问题：

1. **能回答的问题**：展示引用卡片、来源 quote 和合法引用状态。
2. **资料外问题**：展示有限检索重试和拒答。
3. **需要多轮的问题**：复用同一 `thread_id`，展示 history 进入下一轮。

如果准备了测试文档，还可演示：

- 错误码或接口名，说明 FTS5 的价值。
- 文档中包含“忽略之前指令”，展示 `security_flags`。
- 构造无引用 Fake LLM 测试，说明系统只修复一次。

### 6.4 展示工程证据

```bash
python -m pytest -p no:cacheprovider
ruff check .
python scripts/eval_retrieval.py --file data/eval/sample_retrieval.jsonl
```

不要只展示绿色测试结果；选一个测试说明它防止了什么回归。

## 7. 指标使用规范

### 7.1 可以写进简历的条件

一个数字至少应保存以下信息：

- Git commit SHA。
- 评测集名称、版本、样本数和标签规则。
- embedding 与 reranker 模型。
- chunk、topK、RRF 权重和门控配置。
- CPU/GPU、内存和操作系统。
- 是否预热、重复次数和并发。
- 原始 JSON 报告，而不只是截图。

对比实验必须使用同一数据、同一硬件和同一评判规则。

### 7.2 推荐指标模板

仅在真实运行后替换：

> 在 `[评测集版本，N 题]` 上，hybrid + rerank 相比 dense-only baseline 将 Recall@5 从 `[A]` 提升至 `[B]`，MRR 从 `[C]` 提升至 `[D]`；在 `[硬件，并发 C]` 下检索 p50/p95 为 `[X/Y ms]`。

如果只运行了当前脚本，可以报告：

- Recall@5/10。
- MRR。
- nDCG@5/10。
- 检索 mean、p50、p95。
- 基于 `should_answer` 的门控误拒答率、错误放行率与 Precision/Recall（不是 LLM 最终拒答质量）。

不能从当前脚本推导：

- 答案正确率。
- 幻觉下降百分比。
- 引用语义准确率。
- LLM 生成答案的正确性与最终拒答质量。
- 并发吞吐量。
- 端到端 LLM TTFT。

### 7.3 没有指标时的正确写法

写：

> 建立版本化检索评测脚本，支持 Recall、MRR、nDCG 和延迟报告，为 chunk、召回与 rerank 参数调优提供回归基线。

不要写：

> 检索准确率提升 40%，幻觉降低 80%。

## 8. 禁止虚构或夸大的表述

| 不应使用 | 原因 | 建议替换 |
|---|---|---|
| “生产级”“已大规模落地” | 当前是单进程、本地文件和 SQLite 作品集部署。 | “production-minded 工程实践”“可复现本地部署”。 |
| “支持百万文档/高并发” | 没有相应数据规模和压测报告。 | 写实际测试规模与硬件。 |
| “完全消除幻觉” | RAG 和引用格式校验都不能保证。 | “证据不足时拒答，并校验来源编号”。 |
| “引用事实全部正确” | 当前不做逐 claim 语义蕴含。 | “校验引用存在且属于本次上下文”。 |
| “实时 token 流式输出” | 当前 SSE 是节点级事件。 | “提供 LangGraph 节点级 SSE 进度”。 |
| “异步任务可恢复” | JobRegistry 在内存中。 | “提供单进程后台导入和任务状态查询”。 |
| “多租户权限系统” | 只有可选共享 API Key。 | “为非本地部署提供可选共享密钥边界”。 |
| “多智能体协作” | 当前是单 Agent 状态图。 | “有界 Agentic Workflow”。 |
| “MCP 可管理知识库” | MCP 只读。 | “通过 MCP 暴露只读检索和问答能力”。 |
| “完整 RAG 评测体系” | 当前主要是离线检索指标。 | “建立确定性检索评测基础”。 |

## 9. 推荐继续补齐的证据

按招聘价值排序：

1. 在现有 32 题开发集之外冻结独立保留集，增加答案 span 和人工复核。
2. 增加 dense-only、sparse-only、hybrid、hybrid+rerank 消融报告。
3. 把已有门控误拒答/错误放行扩展到真实模型最终回答评测，注意二者口径不同。
4. 增加 claim-to-citation 人工标注集，而不是直接依赖未经校准的 LLM Judge。
5. 记录 1k/10k/100k chunks 下的检索延迟、RSS 和索引耗时。
6. 增加真实 Qdrant 的集成测试和一个 UI 端到端测试。
7. 若要声称可恢复后台任务，再引入持久化队列；否则保留当前简单实现。

每完成一项，再把对应结果加入简历。先有证据，后写指标。
