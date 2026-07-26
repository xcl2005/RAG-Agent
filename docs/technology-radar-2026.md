# RAG Agent 技术雷达与架构决策（2026）

> 最后核对日期：2026-07-26
> 适用范围：本仓库的 Agent 编排、模型调用、检索、协议互操作与后续演进
> 说明：本文记录技术选择及其边界，不声称任何尚未通过本仓库评测集验证的性能提升。

## 1. 结论先行

本项目不把“Agent”理解为不受约束地循环思考，也不为了简历关键词堆叠多个 Agent 框架。当前选择是：

- 用 **LangGraph** 作为唯一的顶层编排和状态持久化层。
- 在少数节点中让模型做受约束的决策，例如查询规划和基于证据生成答案。
- 用确定性代码完成检索、RRF 融合、证据门控、引用校验、重试上限和结果收口。
- 默认使用 **OpenAI Responses API**；保留 Chat Completions 仅用于兼容部分 OpenAI-compatible 服务。
- 用 **Dense + Sparse Hybrid Retrieval + CrossEncoder Rerank** 作为当前检索主线。
- 采用一个可选、只读的 **MCP** 接口；暂缓 A2A 和 GraphRAG。

这不是从 workflow “升级成” agent，而是把二者放在合适的位置：workflow 提供可预测性、可恢复性和可测试性，模型只在需要语义判断的节点获得有限自主权。Anthropic 的官方工程文章也将两者区分为“预先定义代码路径的 workflow”和“由模型动态决定过程与工具使用的 agent”，并建议优先采用能满足需求的最简单方案：[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)。

## 2. 技术雷达

| 技术 | 当前决策 | 在本项目中的角色 | 重新评估条件 |
| --- | --- | --- | --- |
| LangGraph | **采用** | 唯一顶层工作流、状态和 checkpoint 编排 | 发生不兼容的大版本升级，或持久化需求超出当前后端 |
| OpenAI Responses API | **采用** | 官方 OpenAI 端点的默认模型调用路径 | 上游 API 发生迁移要求，或目标供应商不支持 Responses |
| Chat Completions | **兼容保留** | DeepSeek、Qwen 等兼容端点的降级路径 | 所有目标供应商都稳定支持 Responses 后可移除 |
| OpenAI Agents SDK | **暂不采用** | 不与 LangGraph 竞争顶层 agent loop | 若未来移除 LangGraph，并转为纯 OpenAI-first 运行时 |
| Hybrid Retrieval + Rerank | **采用** | 召回、融合和二阶段精排主线 | 必须根据仓库评测集持续校准权重、阈值和 top-k |
| MCP | **采用，可选依赖** | 向外部 Agent/客户端提供只读知识库工具 | 远程部署前补齐 OAuth、权限和网络安全设计 |
| A2A | **暂缓** | 当前没有独立部署的 Agent-to-Agent 协作需求 | 出现多个独立身份、独立生命周期的远程 Agent 服务 |
| GraphRAG | **暂缓** | 当前语料和问题类型尚未证明需要知识图谱索引 | 关系型、全局归纳问题在基准中持续失败，且收益覆盖索引成本 |
| 无界反思 / Agent swarm | **不采用** | 不属于当前问题的必要复杂度 | 只有在可复现评测证明单工作流无法完成时再讨论 |

## 3. Workflow 与 Agent：为什么选择“有边界的自主性”

### 3.1 当前工作流

仓库中的主链路可以概括为：

```text
initialize
  -> plan_queries
  -> retrieve
  -> grade_evidence
     -> 证据不足：有限次数重新规划，最终拒答
     -> 证据充分：generate_answer
  -> validate_citations
     -> 最多修复一次引用
     -> finalize
```

其中，模型负责：

1. 生成互补且结构化的检索查询；
2. 根据已检索证据生成答案；
3. 必要时进行一次引用修复。

代码负责：

1. 输入清洗、状态转换和 checkpoint；
2. Dense/Sparse 检索、RRF 融合与 rerank；
3. 证据阈值、重试次数和引用编号校验；
4. 拒答、错误处理、trace 事件和资源收口。

这种划分便于单元测试和故障定位，也避免模型自行扩大工具权限、重复调用或无限反思。LangGraph 官方文档说明，checkpoint 以 thread 为单位保存图状态，可支持容错、记忆、人机协作和 time travel：[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)。如果未来加入写操作，应在危险动作前使用 `interrupt()`；恢复后节点会从开头重新执行，因此中断前的副作用必须幂等：[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)。

### 3.2 为什么不叠加 OpenAI Agents SDK

OpenAI Agents SDK 提供工具、handoff、guardrail、session 和 tracing，是成熟的 OpenAI-first Agent 运行时：[Agents SDK](https://openai.github.io/openai-agents-python/)。但本项目已经由 LangGraph负责：

- 图路由；
- 状态和线程；
- 重试与退出条件；
- 持久化；
- 节点级可观测信息。

再引入 Agents SDK 作为第二个顶层循环，会产生两套状态、重试和 trace 语义，使故障边界更难解释。当前只使用薄模型客户端，由 LangGraph 节点发起小而明确的模型调用。若未来决定彻底移除 LangGraph，才应重新比较 Agents SDK，而不是让两个运行时嵌套。

## 4. Responses API 决策

OpenAI 当前建议新项目使用 Responses API。它提供统一的多轮、工具调用和内置工具接口，并可配合 Structured Outputs；官方迁移文档将其列为新项目推荐路径：[Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)。

本仓库的具体策略是：

- `llm_api_mode="responses"` 为默认值；
- 使用 JSON Schema 约束查询规划输出，并在进入图状态前通过 Pydantic 再校验；
- 企业知识库内容可能敏感，因此默认 `llm_store_responses=false`；
- 会话和恢复状态由本地 LangGraph checkpointer 管理，不把供应商侧存储作为唯一状态源；
- `chat_completions` 只作为第三方 OpenAI-compatible 服务的兼容路径；
- 模型名、端点和密钥均为部署配置，不让业务代码依赖某个固定模型快照。

稳定性提醒：

- Responses API 是 API 能力，不使用 Python 包式的语义版本号；应同时关注 API 文档和 `openai` SDK 变更。
- 本项目当前约束为 `openai>=2.48,<3`，升级时需运行结构化输出、token usage 和异常处理测试。
- Assistants API 已弃用，并计划于 **2026-08-26** 关闭；不应为本项目新增 Assistants 依赖。
- Agent Builder 计划于 **2026-11-30** 关闭。本项目使用代码内工作流，不依赖该产品。
- 上述日期以 OpenAI 官方弃用页面为准：[OpenAI API deprecations](https://developers.openai.com/api/docs/deprecations)。

## 5. LangGraph 决策

本仓库采用 `langgraph>=1.2.9,<2`，并使用 SQLite checkpointer 保存线程状态。选择 LangGraph 的理由不是“图看起来更像 Agent”，而是：

- 分支和终止条件可以直接在代码中审查；
- 检索重试和引用修复都有明确上限；
- 状态可以 checkpoint，进程失败后具备恢复基础；
- 节点可以单独注入依赖并做确定性测试；
- 后续若出现高风险工具，可加入 interrupt 和人工审批。

截至 2026-07-26：

- LangGraph Python 当前稳定版为 **1.2.9**，发布于 **2026-07-10**：[PyPI](https://pypi.org/project/langgraph/)、[1.2.9 release](https://github.com/langchain-ai/langgraph/releases/tag/1.2.9)。
- 本项目限制 `<2`，避免未来大版本自动进入 CI 或生产环境。
- `DeltaChannel` 等文档中标注 beta 的能力不进入当前核心设计；采用新能力前必须检查稳定性标记并增加迁移测试。

当前图只有知识检索与回答，不执行外部写操作，因此没有为了展示功能而强行加入人工审批节点。将来若增加发邮件、修改工单、删除文件或付费调用，审批和幂等性才是上线前置条件。

## 6. Hybrid Retrieval + Rerank 决策

### 6.1 已采用的检索链

当前实现为：

```text
原问题 + 受约束的查询改写
  -> Qdrant Dense Retrieval
  -> SQLite FTS5 Sparse Retrieval
  -> Weighted Reciprocal Rank Fusion
  -> CrossEncoder Rerank
  -> Evidence Gate
  -> Grounded Answer + Citation Validation
```

Dense retrieval 擅长语义近似，Sparse retrieval 擅长错误码、编号、专有名词和原文精确匹配。RRF 使用排名而不是直接混合两种不可比的原始分数；CrossEncoder 只处理融合后的较小候选集，承担二阶段精排。OpenAI 当前 Retrieval 文档也把 query rewriting、hybrid search 权重、ranking options 和 score threshold 作为检索配置能力：[Retrieval guide](https://developers.openai.com/api/docs/guides/retrieval)。二阶段检索与 rerank 的职责可参考 Pinecone 官方说明：[Rerank results](https://docs.pinecone.io/guides/search/rerank-results)。

### 6.2 不做未经验证的质量承诺

“加入 rerank”不等于自动变准。以下参数都依赖语料和问题分布：

- Dense/Sparse 权重；
- RRF `k`；
- 各路召回 top-k；
- rerank 候选数和最终 top-k；
- reranker 分数阈值；
- dense cosine 与 sparse token coverage 门槛；
- chunk 大小和 overlap。

因此，本文只说明架构动机，不写“准确率提升 XX%”之类未经验证的数据。任何性能结论都应来自固定版本的数据集、明确的指标、可复现命令和对照配置。至少应分别观察 retrieval recall、排序质量、引用有效性、拒答行为、延迟和模型调用成本，不能只看最终答案是否“像是正确”。

### 6.3 引用和 grounding

本项目将来源列表和答案引用分开处理，并在生成后校验引用编号。进一步演进时，应优先增加“引用内容是否真正支持对应陈述”的语义评测，而不是允许模型生成任意 URL 或文件名。OpenAI 官方引用指南建议使用稳定来源 ID、可定位的引用单位，并在渲染前解析和验证引用：[Citation formatting](https://developers.openai.com/api/docs/guides/citation-formatting)。

## 7. MCP：采用，但保持小而只读

MCP 解决的是 Agent/客户端如何发现并调用工具、读取资源，而不是替代 LangGraph 的内部编排。本仓库把 MCP 作为可选依赖，提供：

- `search_knowledge_base`：返回排序后的证据；
- `ask_knowledge_base`：运行完整的有界 RAG 工作流；
- 已索引来源资源；
- 一个 evidence-first 的提示模板。

这些能力有意保持只读，不通过 MCP 暴露任意服务器文件导入、索引清空或系统命令。这样可以展示协议互操作性，同时控制攻击面。

截至 2026-07-26：

- MCP 官方当前协议版本为 **`2025-11-25`**：[Versioning](https://modelcontextprotocol.io/docs/learn/versioning)、[Specification](https://modelcontextprotocol.io/specification/2025-11-25)。
- 项目将 Python SDK 约束为 `mcp[cli]>=1.28,<2`。在 SDK v2 最终发布并完成迁移测试前，不预先放开 major version。
- 日期形式的 draft 或 RC 不能自动等同于稳定协议；客户端与服务器还需要在初始化阶段完成版本协商。
- 当前默认本地 `stdio`，也保留 `streamable-http` 配置。若部署远程 HTTP MCP，必须补充 OAuth 2.1、token audience 校验、最小权限、HTTPS 和 SSRF 防护。官方安全建议明确禁止 token passthrough：[MCP security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)。

## 8. A2A：暂缓

A2A 面向独立 Agent 之间的通信，包含 Agent Card、Message、Task、Artifact、流式结果和长任务状态。它与 MCP 的边界不同：

- MCP：Agent 调用工具或访问资源；
- A2A：具有独立身份和生命周期的 Agent 与 Agent 协作。

官方说明见 [A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)。

当前仓库只有一个 RAG 服务和一套 LangGraph 工作流，没有独立部署的规划 Agent、检索 Agent、审批 Agent 或外部组织 Agent。把内部 Python 节点包装成 A2A 服务只会增加网络、身份、任务状态和故障处理成本，不能自然提高回答质量，因此暂缓。

截至 2026-07-26，A2A 稳定线为 **v1.0**，当前补丁版本为 **v1.0.1**：[A2A specification](https://a2a-protocol.org/latest/specification/)、[v1.0.1 release](https://github.com/a2aproject/A2A/releases/tag/v1.0.1)。出现以下需求时再重新评估：

1. 至少两个 Agent 独立部署和扩缩容；
2. Agent 之间需要跨进程、跨团队或跨组织协作；
3. 任务需要异步运行、状态查询、流式 Artifact 或 push notification；
4. 这些需求无法用普通服务 API 或 MCP 工具更简单地完成。

## 9. GraphRAG：暂缓

Microsoft GraphRAG 会从非结构化文本中抽取实体、关系和 claims，做社区发现与多层级报告，再支持 Local、Global、DRIFT 等查询方式。它尤其适合：

- 需要跨大量文档理解实体关系的问题；
- 需要对整个语料做主题或社区级全局归纳的问题；
- 普通 chunk 检索持续漏掉的多跳关系问题。

官方概览见 [GraphRAG indexing](https://microsoft.github.io/graphrag/index/overview/) 和 [Query engine](https://microsoft.github.io/graphrag/query/overview/)。

当前项目的目标是可复现的企业文档问答，现有 hybrid + rerank 已覆盖语义召回、精确匹配和二阶段排序。仓库还没有一套能证明“关系型或全局问题是主要失败来源”的基准，因此现在引入实体抽取、关系图、社区摘要和新增存储，会让摄取成本、配置和运维复杂度显著上升，却没有经过评测证明的收益。

截至 2026-07-26，Microsoft GraphRAG 最新发布版为 **v3.1.0（2026-05-28）**：[Microsoft GraphRAG repository](https://github.com/microsoft/graphrag)。其仓库明确提醒：

- 该代码是方法展示，并非 Microsoft 正式支持的产品；
- 建图索引可能成本较高；
- 开箱即用的提示未必适合所有数据，官方建议针对数据做 prompt tuning；
- 小版本之间也可能需要刷新配置。

只有在加入关系型/全局问题评测集，并证明当前方案存在稳定缺口后，才应做一个隔离的 GraphRAG 实验分支，与现有方案比较质量、索引时间、查询延迟和成本。没有对照实验时，不把 GraphRAG 写进主依赖。

## 10. 版本与稳定性提醒

| 组件 | 截至 2026-07-26 的状态 | 本项目策略 |
| --- | --- | --- |
| OpenAI Responses API | 新项目推荐接口；无独立语义版本号 | 默认使用，SDK 保持 `<3`，用集成测试验证升级 |
| OpenAI Assistants API | 已弃用；2026-08-26 关闭 | 不采用 |
| OpenAI Agents SDK Python | 最新 **0.18.3**，2026-07-17 发布 | 不作为第二套编排层；仅保留技术观察 |
| LangGraph Python | 稳定版 **1.2.9**，2026-07-10 发布 | `>=1.2.9,<2` |
| MCP Protocol | Current：**2025-11-25** | 对齐 current 规范；SDK 暂留 v1 major |
| A2A | 稳定线 **v1.0**；当前 **v1.0.1** | 暂缓，等待真实跨 Agent 场景 |
| Microsoft GraphRAG | 最新 **v3.1.0**，2026-05-28 发布 | 暂缓，先建立能证明需求的评测集 |

OpenAI Agents SDK 的版本来源：[openai-agents-python releases](https://github.com/openai/openai-agents-python/releases/latest)。

## 11. 后续升级原则

1. **先定义失败问题，再引入技术。** A2A、GraphRAG 或多 Agent 必须对应可复现的现有缺口。
2. **一个顶层编排器。** 除非完成迁移，不让 LangGraph 和另一个 Agent SDK 同时拥有循环、状态与重试控制权。
3. **协议与 SDK 分开看。** MCP 协议版本稳定，不代表某个语言 SDK 的下一个 major 已稳定。
4. **升级必须可回归。** Responses、LangGraph、embedding、reranker 或索引格式升级后，运行相同评测集。
5. **不跨分数体系硬比较。** Dense、BM25/FTS、RRF 和 CrossEncoder 分数含义不同，应分别校准阈值。
6. **安全优先于自主性。** 检索文档和工具输出始终是不可信数据；新增外部副作用必须有权限、审批、幂等和审计。
7. **简历描述以证据为准。** 可以说明设计、实现和测试覆盖；只有得到可复现结果后，才报告具体质量、延迟或成本变化。

## 12. 一手资料索引

- OpenAI：[Responses API migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)、[Retrieval](https://developers.openai.com/api/docs/guides/retrieval)、[Citation formatting](https://developers.openai.com/api/docs/guides/citation-formatting)、[Deprecations](https://developers.openai.com/api/docs/deprecations)
- LangGraph：[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、[PyPI](https://pypi.org/project/langgraph/)
- MCP：[Versioning](https://modelcontextprotocol.io/docs/learn/versioning)、[2025-11-25 specification](https://modelcontextprotocol.io/specification/2025-11-25)、[Security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- A2A：[Specification](https://a2a-protocol.org/latest/specification/)、[A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)、[v1.0.1 release](https://github.com/a2aproject/A2A/releases/tag/v1.0.1)
- Microsoft GraphRAG：[Repository](https://github.com/microsoft/graphrag)、[Indexing overview](https://microsoft.github.io/graphrag/index/overview/)、[Query overview](https://microsoft.github.io/graphrag/query/overview/)
- Anthropic：[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
