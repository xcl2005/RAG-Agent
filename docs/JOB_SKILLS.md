# Agent Backend / AI Application 招聘技能矩阵

> 版本：2026-09-06，第一批样本。目标不是把所有 JD 关键词都塞进项目，而是建立“招聘需求 → 技能树 → 项目证据 → 学习/升级优先级”的长期基线。
>
> **重要边界：本文件当前只完成第一批高质量、可追溯样本，不能宣称覆盖了全部公司或全部岗位。** 后续继续补字节、阿里、腾讯、美团、小红书、快手、华为、蚂蚁、小米和更多 AI Startup/海外公司，并按实习/校招/社招分层统计。

## 1. 我们到底在研究哪些岗位

不要只搜索“Agent 后端”。现在相近岗位名称非常分散，但能力高度重叠：

- Agent 后端研发
- Agent 引擎 / Agent Runtime
- Agent Infra
- AI 应用研发
- 大模型应用研发
- LLM Application Engineer
- Applied AI Engineer
- AI Agent Engineer
- AI 全栈 / AI Native 产品研发
- Agent Platform / Agent Harness
- RAG Engineer
- Backend Engineer, AI/Agents

对本项目最有价值的不是职位标题，而是这些岗位反复出现的共性：

**Agent 执行链路 + 后端工程 + 评测/可观测 + 安全/可靠性 + RAG/Context。**

这意味着项目后续主线应该从“能做 RAG”升级为“能把 Agent/LLM 做成可靠后端系统”。

## 2. 第一批官方招聘样本

### 2.1 百度：Agent 后端研发工程师（J103882，2026-07-29）

来源：<https://talent.baidu.com/jobs/detail/SOCIAL/d1876313-6604-4e8d-bbcc-0dca5be4e51b>

JD 直接出现：

- Agent 云上基础设施
- 推理链路工程
- Agent 网关
- 高性能链路
- 数据闭环
- Agent Infra / Agent Harness
- 系统设计、集成测试、部署与运维
- 操作系统、网络、数据库
- Go，多语言适应
- 编程与算法
- 设计模式、代码质量

**项目含义：** 即使岗位标题写 Agent，底座仍然是后端/系统工程。只会 Prompt、LangChain 或向量库不够。

### 2.2 百度：Agent 引擎开发工程师（J103885，2026-07-29）

来源：<https://talent.baidu.com/jobs/detail/SOCIAL/d56ce9b0-296b-4615-9497-115968d4fc14>

这是当前最适合做“生产级 Agent Backend 能力树”的样本之一。JD 包含：

- Agent 运行引擎
- Tool / Skills 插件系统
- Long-term Memory
- 多模型路由
- 异步消息处理
- 状态持久化
- 限流
- retry
- trace
- 全链路日志
- 资源隔离
- sandbox
- 工具调用权限
- 行为监控 / 异常检测
- human-in-the-loop 审批门
- 高危操作确认
- 运行时策略
- 自主规划 / reflection
- 多 Agent
- Redis
- PostgreSQL
- Kafka
- 事件驱动
- 负载均衡
- 熔断降级
- OAuth / JWT
- prompt injection / tool abuse / memory/file escape / credential leakage
- LLM、Tool Calling、ReAct / Plan-and-Execute、RAG、Embedding、Vector DB

**项目含义：** 这已经不是“一个 Agent 框架”能覆盖的岗位。真正核心是运行时、状态、可靠性、安全和普通后端能力。

### 2.3 百度：云原生 Agent Infra 高级研发工程师（J100117，2026-07-21）

来源：<https://talent.baidu.com/jobs/detail/SOCIAL/4b326f6b-2c39-461c-ae64-69b4201c680e>

主要技能：

- Agent sandbox / gateway / observability
- 多租户隔离
- 资源管控、网络接入、安全防护
- Multi-Agent 大规模编排、调度、治理、自恢复
- CLI / MCP / SDK / Skill
- Go / Python / C++
- Linux、网络、操作系统
- Kubernetes / Operator
- Docker / containerd / Kata Containers / gVisor / Firecracker
- 分布式计算/存储/调度
- 高可用、弹性伸缩、性能优化
- Agent execution model
- context engineering / Harness engineering
- Serverless
- Prometheus / Grafana / Loki / OpenTelemetry / Langfuse 类可观测

**项目含义：** 这是进阶 Infra 路线。对当前求职项目，先理解并记录；Kubernetes、虚拟化沙箱和大规模调度不应为了堆关键词立刻实现。

### 2.4 百度：AI Native 产品研发工程师（J99617，2026-07-21）

来源：<https://talent.baidu.com/jobs/detail/SOCIAL/40033338-ccd0-4a3d-b2ac-fc47e32a109e>

主要技能：

- AI Coding / Agent Workflow
- 长程任务
- 项目生成、调试、部署
- Agent task orchestration
- context management
- tool calling
- execution state tracking
- result evaluation
- SaaS / 全栈 / 上线交付
- AWS/GCP/Azure
- database / queue / object storage / logs / serverless / containers
- RAG / multi-turn task execution
- Agent eval：成功率、可恢复性、工具调用质量、完成度、用户满意度

**项目含义：** AI 全栈岗位强调“端到端交付真实用户产品”，不只是后端框架知识。

### 2.5 京东：软件开发岗（AI 应用方向，2026-07-14）

来源：<https://zhaopin.jd.com/web/job-info-detail?requementId=220736>

JD 包括：

- AI Agent / Copilot / Workflow / multi-step task
- planning
- tool calling
- routing
- context management
- permission
- failure fallback
- LLM / RAG / Embedding / Vector DB / enterprise KB / internal API
- offline eval / regression / human feedback / online metrics / failure analysis
- logging / trace / tool chain / latency
- Python 或 TypeScript/Node.js/Java/Go
- LangGraph / LangChain / Semantic Kernel / AutoGen / CrewAI 等模式或框架
- API、database、cache、async task、microservice、container、cloud

**项目含义：** 这是最典型的“Agent + Backend + Evaluation + Observability”综合岗位。

### 2.6 OpenAI：Software Engineer, API Agents（2026-09 在招）

来源：<https://openai.com/careers/software-engineer-api-agents-san-francisco/>

公开描述直接提到：

- shared agent harness / tools / infrastructure
- search and connected context
- computer use
- memory
- delegation
- multi-agent coordination
- safe execution
- reliable services and abstractions
- long-running workflows

**项目含义：** Agent 工程的核心不是“会调用模型”，而是如何让模型可靠地找上下文、用工具、保持状态、长时间执行并安全行动。

### 2.7 OpenAI：Applied AI Engineer, Codex Core Agent

来源：<https://openai.com/careers/applied-ai-engineer-codex-core-agent-san-francisco/>

主要能力：

- real-world agent behavior
- long-horizon workflow
- eval / regression / failure mode / edge case
- prompting
- tool-use strategy
- context construction
- production failure analysis
- robustness / reliability
- feedback loop / data system
- solve rate / usefulness / economic value
- token / latency / reliability / cost / capacity

**项目含义：** Agent 的质量必须能被测量。后续项目不能只说“加了 Agent 功能”，必须有任务成功率、失败分类、延迟和成本等证据。

### 2.8 OpenAI：Backend Software Engineer, GTM Innovation

来源：<https://openai.com/careers/backend-software-engineer-gtm-innovation-san-francisco/>

主要能力：

- persistent agents
- durable workflow orchestration
- long-running agent loops
- context
- memory
- tools
- permissions
- production backend foundation

**项目含义：** durable execution、权限模型和长期状态是普通 Demo 与生产 Agent 的明显分界。

### 2.9 Anthropic：AI Engineer, GTM Claudification

来源：<https://job-boards.greenhouse.io/anthropic/jobs/5390966008>

主要能力：

- autonomous agent
- human oversight / approval gates / escalation
- agent eval in dev and production
- model/tool-call instrumentation
- observability
- MCP server
- Agent Skills
- web application
- production monitoring
- ROI / business measurement
- shared codebase / review / quality convention

**项目含义：** HITL、评测、MCP、可观测、业务效果是 Agent 应用工程的重要组成，不应只看模型链路。

### 2.10 Anthropic：Applied AI Engineer, Enterprise Tech

来源：<https://job-boards.greenhouse.io/anthropic/jobs/5057647008>

主要能力：

- advanced prompt engineering
- agent development / frameworks
- evaluation frameworks
- transcript analysis
- MCP
- deployment at scale
- Python / TypeScript
- production application

**项目含义：** Applied AI 岗位既要模型/Agent 判断力，也要求真实生产软件能力。

## 3. 去重后的能力树

下面是第一批 JD 去重后的完整技能树。频率等级目前只是**第一批样本的定性判断**，后续增加更多公司后才能做正式统计。

### A. 编程与计算机基础

| 技能 | 第一批频率 | 项目当前状态 | 优先级 |
|---|---|---|---|
| Python | 很高 | 已实现/大量使用 | P0 |
| Go | 国内 Agent Backend/Infra 高频 | 未实现 | P1：理解并可独立写基础服务，不必立刻重写项目 |
| TypeScript / Node.js | Agent 引擎/全栈常见 | 前端 JS；Node 后端未实现 | P1 |
| Java | 后端通用备选 | 未实现 | P2 |
| C/C++ | Infra/系统岗加分 | 未实现 | P2/P3 |
| 数据结构与算法 | 很高 | 代码中使用；面试需独立训练 | P0 |
| OS / Network / Database | 很高 | 部分实践，系统知识文档不足 | P0 |
| Linux | 很高 | Docker/运行涉及；系统学习不足 | P0 |
| 设计模式 / 代码质量 | 常见 | 部分体现 | P1 |

### B. Backend Engineering

| 技能 | 第一批频率 | 项目当前状态 | 优先级 |
|---|---|---|---|
| REST API / FastAPI | 很高 | 已实现 | P0 |
| SSE / streaming | 常见 | 已实现节点 SSE；非 token streaming | P0 |
| async / await | 很高 | 部分 | P0 |
| concurrency / high concurrency | 很高 | 部分；缺系统压测 | P0 |
| PostgreSQL/MySQL | 很高 | SQLite 已实现；Postgres 未实现 | P1 |
| Redis | 很高 | 未实现 | P1 |
| Kafka / MQ | 中高 | 未实现 | P1 |
| task queue / durable jobs | 高 | 当前内存 JobRegistry，不是持久队列 | P0/P1 |
| cache | 高 | 未形成独立缓存层 | P1 |
| idempotency | 高价值 | 入库已实现幂等思想 | P0 |
| timeout / retry | 很高 | Agent 有界重试；通用服务治理不完整 | P0 |
| fallback / degradation | 很高 | 部分 | P0 |
| rate limiting | 很高 | 未实现完整生产限流 | P1 |
| circuit breaker | 国内高并发岗常见 | 未实现 | P2 |
| event-driven architecture | 常见 | 未实现 | P1 |
| authn/authz | 高频 | API key 基础；OAuth/JWT/RBAC 未实现 | P1 |
| microservice | 常见 | 单体 | P2：先理解，不为关键词拆服务 |
| Docker | 很高 | 已实现 | P0 |
| Cloud | 常见 | 本地 Docker 为主 | P1 |

### C. RAG / Retrieval / Context

| 技能 | 项目当前状态 | 下一步 |
|---|---|---|
| parsing | 已实现 | 补 OCR/失败状态前先完善教材 |
| chunking | 已实现 | 做参数对照实验 |
| metadata | 已实现部分 | 继续明确过滤与身份语义 |
| embedding | 已实现 | 补模型切换/维度/成本教学 |
| dense retrieval | 已实现 | 纳入完整消融 |
| sparse / FTS | 已实现 | 纳入完整消融 |
| hybrid retrieval | 已实现 | 需要更完整证据 |
| RRF | 已实现 | 教学 + 参数实验 |
| reranker | 已实现 | 需要独立增益/延迟评测 |
| query planning/rewrite | 已实现 | 需要真实模型评测 |
| metadata filtering | 部分 | P1 |
| context selection | 已实现 | 继续做 token-aware / diversity 实验 |
| citation | 已实现编号/结构校验 | 不能称事实验证；需支持度评测 |
| grounding / faithfulness | 部分 | P0/P1 |
| refusal / abstention | 已实现证据门控 | P0：做错误放行/误拒答评测 |
| RAG eval | 部分 | P0 |

### D. Agent Core

| 技能 | 项目当前状态 | 优先级 |
|---|---|---|
| Agent workflow / graph | 已实现 LangGraph 有界流程 | P0 |
| Tool / Function Calling | MCP 被外部调用；通用 Agent tool loop 未完整实现 | P0 |
| Tool Registry / schema / validation | 未完整实现 | P0/P1 |
| ReAct / Plan-and-Execute | 查询规划有部分思想；非完整通用 ReAct | P1 |
| routing | 部分 | P1 |
| state management | SQLite checkpoint 已实现 | P0 |
| short-term memory | 会话状态部分实现 | P0 |
| long-term memory | 未实现 | P1 |
| context management | 已实现一部分 | P0 |
| context compression / token budget | 字符预算已有；token-aware 不完整 | P0/P1 |
| model routing | 未实现 | P1 |
| durable / resumable execution | 未实现 | P0/P1 |
| long-running task | 未实现 | P1 |
| HITL approval | 未实现 | P1 |
| multi-agent / delegation | 未实现 | P2，先证明单 Agent 场景需要 |
| MCP | 已实现只读 server | P0 |
| Skills / Plugins | 未实现通用体系 | P1 |
| Agent Harness / Runtime | 项目已有局部骨架，不能称完整 Runtime | P0/P1 |
| browser/computer use | 未实现 | P2/P3 |

### E. Evaluation / Observability / Reliability

这是第一批 JD 最值得项目加强的领域之一。

- offline eval
- regression test
- online metric
- human feedback
- failure taxonomy / failure analysis
- task success rate
- tool-call success rate
- answer quality / groundedness
- latency
- token usage
- cost
- trace
- logs
- metrics
- production monitoring
- retry / timeout / fallback
- recoverability
- deterministic replay / checkpoint（进阶）

当前项目已有 trace、节点耗时、检索评测与测试基础，但距离“完整 Agent Eval + production observability”还有明显差距。

### F. Security / Permission

第一批样本已经反复出现：

- authentication
- authorization
- OAuth / JWT
- RBAC / permission model
- multi-tenant isolation
- sandbox
- tool permission
- secrets
- prompt injection
- tool abuse
- credential leakage
- risky action confirmation
- HITL approval
- runtime policy enforcement

当前项目已有 Prompt Injection 基础防护、API key 和文件边界，但不能称完整 Agent security。

### G. Agent Infra（进阶）

- Kubernetes
- Operator
- Docker/containerd
- gVisor / Kata / Firecracker
- distributed scheduling
- elastic scaling
- high availability
- resource isolation
- Serverless
- large-scale sandbox orchestration
- Prometheus / Grafana / Loki / OpenTelemetry

对当前项目：**学习并记录 > 立刻实现。** 只有当项目真正出现多租户、长任务、规模化执行需求时，再逐步升级。

## 4. 当前项目最有价值的已实现能力

基于源码，而不是 README 宣传：

- LangGraph 有界 workflow：`src/rag_agent/agent/graph.py`
- Dense + SQLite FTS5 Hybrid：`src/rag_agent/retrieval/hybrid.py`
- RRF：`src/rag_agent/retrieval/fusion.py`
- reranker：`src/rag_agent/retrieval/reranker.py`
- context / evidence gate / citation：`src/rag_agent/agent/graph.py`
- state/checkpoint：Agent graph + SQLite
- FastAPI / SSE：`src/rag_agent/api/main.py`
- MCP：`src/rag_agent/mcp/server.py`
- ingestion / idempotent indexing：`src/rag_agent/ingest/`
- offline evaluation：`src/rag_agent/evaluation/` + `scripts/eval_*`
- Docker / CI / pytest / coverage

这些能力已经足以作为“Agent Backend / AI Application”项目骨架，但不足以声称生产级 Agent Runtime。

## 5. 当前最大招聘缺口

### P0：最值得下一轮做

1. **通用 Tool Calling / Agent Tool Loop**：真正让 Agent 选择、校验、执行工具，而不是只有知识库 MCP 接口。
2. **Agent Evaluation**：任务成功率、工具调用正确率、失败分类、回归集、成本/延迟。
3. **可靠性**：timeout、retry、fallback、取消、可恢复执行、明确失败状态。
4. **Backend 状态与任务**：从单进程内存 JobRegistry 逐步走向可持久任务；理解 async/concurrency。
5. **Context/Memory**：区分 conversation state、short-term memory、long-term memory；不要把 checkpoint 都叫 memory。

### P1：P0 稳定后

- Redis
- PostgreSQL
- durable queue / MQ
- rate limiting
- auth / JWT / permission
- HITL approval
- model routing
- structured output validation
- OpenTelemetry / Langfuse 类 trace 集成
- cloud deployment

### P2/P3：进阶而非堆关键词

- Multi-Agent
- Kubernetes / Operator
- sandbox virtualization
- distributed Agent Runtime
- browser/computer use
- large-scale scheduling

## 6. 技能进入项目的判定规则

以后任何招聘技能都走这条链：

**招聘出现 → 归类 → 判断频率 → 判断项目是否真的需要 → 先写最小可验证实验 → 实现 → 测试 → 评测 → 文档 → 面试表达。**

项目状态必须使用下面的词，不允许混淆：

- **已讲解**：文档讲过，不代表有代码。
- **有 Demo**：存在最小示例，不代表集成进主链路。
- **已实现**：主项目有真实代码路径。
- **有测试**：存在自动测试覆盖行为。
- **有效果证据**：有可复现实验或指标，且边界写清楚。
- **未实现**：只在 Roadmap / 技能矩阵中。

## 7. 后续招聘调研待办

下一批至少补齐：

- 字节：Seed / AI 应用 / Agent / Search Agent / 后端
- 阿里 / 阿里云：AI 应用、Agent、Agent Infra、AI 架构/后端
- 腾讯：混元、元宝、AI 应用、Agent 平台/后端
- 美团：大模型应用、RAG/Agent、后端
- 小红书：Agent 核心链路、AI 应用后端
- 快手
- 华为
- 蚂蚁
- 小米
- 国内 AI Startup
- Google / Microsoft / Meta / Amazon / Databricks / LangChain 等

正式统计时要额外记录：

- 招聘日期
- 实习 / 校招 / 社招
- 年限
- 城市
- 岗位族
- 必选 / 加分项
- 技能原文
- 去重技能标签

这样才能回答“应届生真正需要什么”，而不是把 5 年经验 Staff Agent Infra 的要求全部压到一个学生项目上。
