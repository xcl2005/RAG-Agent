# Agent Backend / AI Application 招聘技能地图

> 更新：2026-09-06
>
> 目标岗位族：
> **Agent Backend / AI 应用研发 / 大模型应用研发 / AI 全栈 / Agent Infra /
> AI 架构及后端 / LLM Engineering / 智能体研发 / Agent Platform / Agent Runtime / RAG Engineer**
>
> 本文不是“看到一个 JD 关键词就往项目里塞一个框架”。
> 目标是把招聘要求去重成能力树，再映射到项目真实实现状态。
>
> **边界：这里覆盖的是当前检索到、可追溯的一批代表性岗位，不可能宣称穷尽全互联网全部在招职位。**
> 官方页面能读取时优先官方；部分国内岗位只能通过标注“来源于官网”的招聘镜像读取，最终仍以企业官网为准。

# 1. 结论先写

当前最清晰的共同趋势不是“人人都要会 LangChain”，而是：

```text
Agent 执行链路
+ RAG / Context
+ Backend Engineering
+ State / Memory
+ Tool Calling
+ Evaluation
+ Observability
+ Reliability
+ Security / Permission
```

对偏应用工程的求职者，最值得形成的能力画像是：

**能把 LLM/Agent 做成一个可靠、可观察、可评测、可部署的后端系统。**

因此本项目后续定位：

```text
RAG 项目
→ Agent Backend / AI Application Engineering 项目
```

而不是：

```text
RAG
→ 再装十个 Agent 框架
```

---

# 2. 代表性招聘样本

## 2.1 百度：Agent 后端研发工程师

来源：

<https://talent.baidu.com/jobs/detail/SOCIAL/d1876313-6604-4e8d-bbcc-0dca5be4e51b>

出现能力：

- Agent 云上基础设施
- Agent 网关
- 推理链路工程
- Agent Infra / Harness
- 系统设计
- 集成测试
- 部署运维
- OS / 网络 / 数据库
- Go
- 算法与编程
- 设计模式
- 性能

结论：

**Agent 后端底座仍然首先是后端和系统工程。**

---

## 2.2 百度：Agent 引擎开发工程师

来源：

<https://talent.baidu.com/jobs/detail/SOCIAL/d56ce9b0-296b-4615-9497-115968d4fc14>

技能非常完整：

- Agent Runtime
- Tool / Skill
- Memory
- 多模型路由
- 异步消息
- 状态持久化
- 限流
- retry
- trace
- 日志
- sandbox
- 资源隔离
- 工具权限
- 行为监控
- HITL
- 风险操作确认
- Redis
- PostgreSQL
- Kafka
- 事件驱动
- 负载均衡
- 熔断
- OAuth / JWT
- prompt injection
- tool abuse
- credential leakage
- ReAct
- Plan-and-Execute
- RAG
- Embedding
- Vector DB

这是当前最适合拿来定义“Agent Backend 技能树”的样本之一。

---

## 2.3 百度：Agent Infra

来源：

<https://talent.baidu.com/jobs/detail/SOCIAL/4b326f6b-2c39-461c-ae64-69b4201c680e>

出现：

- sandbox
- gateway
- observability
- multi-tenant
- resource isolation
- Multi-Agent scheduling
- CLI / MCP / SDK / Skill
- Go / Python / C++
- Linux
- Kubernetes / Operator
- Docker / containerd
- Kata / gVisor / Firecracker
- distributed scheduling
- high availability
- autoscaling
- execution model
- context engineering
- Serverless
- Prometheus / Grafana / Loki / OpenTelemetry

这类岗位明显更偏 Infra。

当前项目只把它作为进阶路线，不会为了简历关键词立刻实现虚拟化沙箱或 K8s 调度。

---

## 2.4 百度：AI Native 产品研发

来源：

<https://talent.baidu.com/jobs/detail/SOCIAL/40033338-ccd0-4a3d-b2ac-fc47e32a109e>

出现：

- AI Coding
- Agent Workflow
- long-running task
- orchestration
- context management
- tool calling
- execution state
- evaluation
- SaaS
- Cloud
- DB
- queue
- object storage
- logs
- container
- RAG
- multi-turn execution

说明 AI 全栈 / AI Native 岗位很看重：

**把完整产品交付出去。**

---

## 2.5 字节 Seed

官方招聘入口：

<https://seed.bytedance.com/zh/career>

当前可见岗位族包括：

- Code Agent
- 通用 Agent
- 搜索 / Search Agent
- 强化学习
- 大模型算法

这里必须区分：

- **Agent Algorithm / Research**
- **Agent Application / Backend**

前者可能需要 Transformer、RL、后训练、训练框架、论文等；
后者与本项目更加匹配。

不能因为都叫 Agent 就混成一类。

---

## 2.6 阿里云 2027

招聘信息中公开列出的研发类岗位包括：

- AI 应用研发工程师
- AI Agent 研发工程师
- Agent Infra 工程师
- AI 架构及后端工程师
- AI 全栈开发工程师
- AI Infra

参考：

<https://career.nankai.edu.cn/correcruit/content/id/116681.html>

这非常直接地说明：

**“Agent 后端 / AI 应用 / Agent Infra / AI 全栈”已经形成不同但高度重叠的岗位族。**

因此不能只搜一个关键词。

---

## 2.7 腾讯元宝：后台开发

可追溯镜像，标注来源为腾讯官网：

<https://jobs.niuqizp.com/job-vwm55ZzCZ.html>

出现：

- 高并发
- 低延迟
- AIGC backend
- plugin 接入与管理
- Agent 上线平台
- data pipeline
- SLA
- Go / C++ / Python
- RPC
- microservice
- MySQL
- Redis
- MongoDB
- Kafka / RabbitMQ
- Docker / K8s
- Airflow
- LLM application framework

这类岗位给出的信号非常明确：

**传统 Backend 基础不是可选项。**

---

## 2.8 美团：大模型应用后端 / 智能体架构

可读取职位：

<https://www.zhaopin.com/jobdetail/CC383625320J40682693109.htm>

出现：

- Multi-Agent
- Agent system design
- tool/API calling
- planning
- reasoning
- self-adaptation
- business landing
- deployment
- workflow automation

另有大模型应用 / Agent / 对话式 AI / 多模态相关软件岗位。

对项目意味着：

不能只证明“会 RAG”。

还应该能解释：

- agent control flow
- tool interface
- failure handling
- deployment
- evaluation

---

## 2.9 小红书：AI Agent 开发工程师

可追溯镜像，标注来源为小红书官网：

<https://jobs.niuqizp.com/job-vyr5NttZt.html>

这是非常有代表性的 Agent Backend JD。

出现：

- task planning
- ReAct
- state transition
- model/tool alternation
- exception handling
- Tool Registry
- argument validation
- parallel tool calling
- timeout
- retry
- fallback
- trace
- context construction
- history selection
- token budget
- context trimming
- compression
- short-term memory
- long-term memory
- RAG integration

当前项目新增的 Tool Runtime，正是为了补这类能力中的最小可运行子集：

- Registry
- Schema validation
- timeout
- error taxonomy
- trace
- bounded tool loop

但**并行 tool calling、long-term memory、生产级 retry/fallback 仍未完成。**

---

## 2.10 小红书：Agent 产品研发实习

参考：

<https://campus.niuqizp.com/job-vrU5zZ5La.html>

出现：

- Agent Harness
- long-chain / multi-step task
- tool calling
- executor protocol
- task scheduling
- context management
- memory
- permission
- sandbox
- human confirmation
- trace
- replay
- observability

这类 JD 对应的项目升级重点非常清楚：

**Runtime + Security + Observability + Durable Task。**

---

## 2.11 小红书：AI Agent 创作研发

参考：

<https://jobs.niuqizp.com/job-vkk5LLCnZ.html>

出现：

- Agent orchestration
- workflow
- task scheduling
- multimodal
- Prompt Engineering
- Tool Calling
- RAG
- streaming inference
- model routing

说明 AI 全栈 / 产品研发还会更关心：

- UI / product integration
- streaming
- model routing
- multimodal task flow

---

## 2.12 小红书：Agent 引擎架构

参考：

<https://jobs.niuqizp.com/job-vkr5LLLaZ.html>

出现：

- planning
- multi-agent
- tool calling
- memory
- context
- long task
- state management
- resumable execution
- fault tolerance
- degradation
- observability
- gray release
- rollback

其中：

**resumable execution / fault tolerance / observability**

是当前项目很明显的下一阶段缺口。

---

## 2.13 快手：AI Agent 研发

参考：

<https://jobs.ultraai.site/jobs/kuaishou/31829>

出现：

- LLM business application
- Agent
- Agent quality evaluation
- evaluation framework
- metric design
- business scale deployment

最重要的信号：

**Agent Eval 已经不是“加分项”，而是岗位正式职责的一部分。**

---

## 2.14 蚂蚁：Agent Infra

参考：

<https://jobs.ultraai.site/jobs/ant/260811011363087>

出现：

- large-scale Agent collaboration
- scheduling
- management
- sandbox
- gateway
- multi-agent
- tool calling
- memory
- long task
- context engineering
- execution framework

这比普通 AI 应用更偏：

**Agent Runtime / Agent Infra。**

---

## 2.15 蚂蚁：Agent 研发

2027 实习样本：

<https://www.nowcoder.com/jobs/detail/445290>

出现：

- AI native architecture
- memory management
- reasoning strategy
- tool orchestration
- business problem abstraction
- end-to-end implementation

另一 AI Infra / Agent 实习样本：

<https://www.nowcoder.com/jobs/detail/442160>

出现：

- planning
- tool calling
- memory
- dialogue management
- reasoning engine
- AI Infra
- stability
- end-to-end delivery

对学生尤其有参考价值：

**不是所有岗位都要求你先有五年高并发经验，但仍然要求你理解完整 Agent 链路。**

---

## 2.16 华为

官方招聘主页：

<https://career.huawei.com/>

当前可看到：

- AI 人才专项
- AI Infra
- AI 应用
- 软件开发

但本轮没有拿到足够详细、可逐条解析的官方 Agent Backend JD。

因此：

**不编造华为的具体技能频率。**

后续继续补官方明细。

---

## 2.17 小米

官方招聘：

<https://hr.xiaomi.com/website/opportunities.html>

可确认 AI 是招聘方向，但当前公开页面没有被检索到足够详细的 Agent Backend JD。

同样：

**只记录“待补具体 JD”，不虚构技能要求。**

---

# 3. 海外代表样本

## 3.1 OpenAI：API Agents

参考：

<https://openai.com/careers/>

已检索到的 Agent / Applied AI 岗位信号包括：

- agent harness
- tools
- connected context
- computer use
- memory
- delegation
- multi-agent
- safe execution
- long-running workflow
- reliable services

核心不是某个框架，而是：

**安全、状态、工具、执行和可靠性。**

---

## 3.2 OpenAI：Applied AI / Agent

代表性要求：

- real-world agent behavior
- long-horizon workflow
- eval
- regression
- failure analysis
- tool-use strategy
- context construction
- robustness
- feedback loop
- solve rate
- usefulness
- token
- latency
- reliability
- cost

项目后续不能只测：

“RAG 有没有搜到”。

还要逐步测：

“Agent 有没有完成任务”。

---

## 3.3 Anthropic：Applied AI

代表性招聘信号：

- agent development
- MCP
- evaluation
- production monitoring
- deployment
- transcript / failure analysis
- Python / TypeScript
- production application

这和国内 AI 应用岗的共性其实非常高：

**Agent + Software Engineering + Eval。**

---

## 3.4 Amazon AWS AgentCore

参考：

<https://amazon.jobs/en/jobs/10478272/sr-software-development-engineer-agentcore-aws-agentic-ai>

AgentCore Harness 明确涉及：

- model
- instructions
- tools
- skills
- memory
- execution limits
- managed agent loop
- secure execution environment
- session isolation
- identity
- networking
- observability
- deployment lifecycle
- control plane / data plane

这几乎就是生产 Agent Runtime 的完整范式。

---

## 3.5 Amazon AgentCore Memory

参考：

<https://www.amazon.jobs/en-gb/jobs/10502322/software-development-engineer-agentic-ai>

出现：

- short-term / long-term memory
- distributed systems
- scalable
- efficient
- fault tolerant
- architecture
- testing
- deployment

说明 Agent Memory 不是单纯：

“把聊天记录塞数据库”。

生产环境里它仍然是分布式系统问题。

---

## 3.6 LangChain：LangSmith Deployments Backend

参考：

<https://jobs.ashbyhq.com/langchain/cb61f821-d8c4-4ec5-940d-3fd83be63a5f>

出现：

- durable execution runtime
- long-running agents
- distributed queue / worker
- background tasks
- multi-agent coordination
- state persistence
- atomic job claiming
- connection management
- schema evolution
- resumable streaming
- trace
- metrics
- alerting
- Go / Python
- distributed systems
- queueing
- state machines
- DB scaling
- K8s
- cloud

这是 Agent Backend / Runtime 进阶路线非常典型的 JD。

---

## 3.7 LangChain：Observability & Evals Backend

参考：

<https://jobs.ashbyhq.com/langchain/f07c1416-f126-4925-8606-5dd7c5a90f6f>

出现：

- backend service / API
- tracing
- monitoring
- evaluation
- high-volume data
- reliability
- testing
- alerting
- RCA
- Postgres
- Redis
- ClickHouse
- cloud

这说明：

**Eval/Observability 自己也是完整后端系统。**

---

## 3.8 LangChain：Early Career Deployed Engineer

参考：

<https://jobs.ashbyhq.com/langchain/dfbba971-a7e2-4feb-a0d9-8e38a1155134>

这个样本对初级求职更有参考价值。

出现：

- Python
- JavaScript
- systems fundamentals
- agent-based application
- multi-step workflow
- orchestration
- failure handling
- deployment
- technical communication
- production operation

非常适合做学生阶段目标：

**不要求你先实现大规模 K8s Runtime，但要求你真的做过超过“单次 API 调用”的 Agent 应用。**

---

# 4. 去重后的完整技能树

# A. Programming / CS

必须长期学：

- Python
- Go 基础
- Java 基础
- C/C++ 基础
- 数据结构
- 算法
- OOP
- design pattern
- Linux
- Git
- OS
- Network
- HTTP / HTTPS
- TCP
- RPC
- SSE
- WebSocket
- gRPC
- Database fundamentals

优先级：

- Python：P0
- CS 基础：P0
- Go：P1
- Java：P1/P2
- C++：按岗位决定

---

# B. Backend Engineering

高频能力：

- REST API
- FastAPI
- async / await
- thread
- process
- GIL
- concurrency
- high concurrency
- PostgreSQL
- MySQL
- Redis
- MongoDB
- cache
- Kafka
- RabbitMQ
- task queue
- background worker
- streaming
- transaction
- idempotency
- rate limiting
- retry
- timeout
- fallback
- circuit breaker
- distributed lock
- load balancing
- SLA
- microservice
- event-driven architecture
- distributed system
- connection pool
- schema migration
- fault tolerance
- scaling

当前项目：

| 技能 | 状态 |
|---|---|
| FastAPI | 已实现 |
| REST | 已实现 |
| SSE | 已实现节点事件 |
| SQLite | 已实现 |
| Qdrant | 已实现 |
| Background ingestion | 已实现 |
| idempotent ingestion | 已实现 |
| basic retry/failure classification | 部分 |
| Redis | 未实现 |
| PostgreSQL | 未实现 |
| Kafka/RabbitMQ | 未实现 |
| durable queue | 未实现 |
| resumable task | 未实现 |
| rate limit | 未实现 |
| circuit breaker | 未实现 |

---

# C. RAG / Retrieval

完整能力树：

- parsing
- PDF / DOCX / Markdown / HTML
- OCR
- chunk
- overlap
- metadata
- embedding
- vector database
- sparse retrieval
- BM25 / FTS
- dense retrieval
- hybrid retrieval
- RRF
- reranker
- query rewrite
- multi-query
- metadata filter
- context selection
- context compression
- citation
- grounding
- faithfulness
- hallucination
- refusal
- retrieval eval
- end-to-end eval

当前项目：

| 技能 | 状态 |
|---|---|
| parsing | 已实现 |
| chunking | 已实现 |
| embedding | 已实现 |
| Qdrant | 已实现 |
| SQLite FTS5 | 已实现 |
| hybrid | 已实现 |
| weighted RRF | 已实现 |
| reranker | 已实现 |
| multi-query planning | 已实现 |
| context selection | 已实现 |
| citation structure validation | 已实现 |
| refusal / evidence gate | 已实现 |
| retrieval eval | 部分实现 |
| faithfulness eval | 不完整 |
| OCR | 未实现 |

---

# D. Agent Core

高频能力：

- Tool / Function Calling
- Tool Registry
- Tool schema
- argument validation
- parallel tool calling
- timeout
- retry
- fallback
- tool result trace
- ReAct
- planning
- workflow
- routing
- state
- checkpoint
- short-term memory
- long-term memory
- context management
- token budget
- context compression
- model routing
- execution limit
- durable execution
- resumable execution
- long-running task
- HITL
- multi-agent
- delegation
- MCP
- Skill
- Plugin
- Agent Harness
- Agent Runtime
- sandbox
- computer use
- browser use

当前项目：

| 技能 | 状态 | 证据 |
|---|---|---|
| LangGraph bounded workflow | 已实现 + 有测试 | `agent/graph.py` |
| state/checkpoint | 已实现 | LangGraph + SQLite |
| MCP | 已实现只读 | `mcp/server.py` |
| Tool Registry | 已实现独立 runtime + 有测试 | `agent/tooling.py` |
| Tool schema validation | 已实现独立 runtime + 有测试 | Pydantic |
| tool timeout/error taxonomy | 已实现独立 runtime + 有测试 | `agent/tooling.py` |
| bounded tool loop | 有 Demo / 已实现独立 runtime | `scripts/tool_agent.py` |
| knowledge search tool | 已实现只读 | Hybrid Retriever |
| parallel tool calling | 未实现 |
| generic retry/fallback | 不完整 |
| long-term memory | 未实现 |
| durable/resumable execution | 未实现 |
| HITL | 未实现 |
| multi-agent | 未实现 |
| sandbox | 未实现 |

注意：

**独立 Tool Agent runtime 还没有替换主 RAG LangGraph。**

所以不能在简历上写：

> 构建完整生产 Agent Runtime。

更准确的是：

> 在主 RAG 工作流之外实现受限 Tool Agent runtime，加入 Tool Registry、Schema 校验、超时和执行 trace，并复用 Hybrid Retriever 作为只读知识库工具。

---

# E. Context / Memory

必须区分：

### Conversation history

过去对话。

### State

当前任务执行状态。

### Checkpoint

把状态持久化，以便图继续使用。

### Short-term Memory

任务或会话内有选择地保留信息。

### Long-term Memory

跨任务长期可检索、可更新的信息。

### Context Engineering

决定这一次模型到底看到什么。

高频招聘技能：

- history selection
- token budget
- compression
- summarization
- state isolation
- memory retrieval
- memory write
- memory lifecycle
- context relevance
- conflict handling

当前项目：

- checkpoint：有
- context selection：有
- history：有
- character budget：有
- token-aware budget：不完整
- long-term memory：无

---

# F. Evaluation

必须覆盖：

- retrieval recall
- ranking
- gate quality
- final answer correctness
- groundedness
- citation support
- task success
- tool call success
- tool argument correctness
- recovery success
- latency
- token
- cost
- regression
- failure taxonomy
- human feedback
- online metrics

当前：

- unit tests：有
- retrieval eval：有基础
- gate metrics：有基础
- synthetic regression set：有
- Tool runtime behavior tests：有
- full Agent task-success eval：无
- real-model end-to-end eval：不完整
- cost regression：无
- online feedback：无

---

# G. Observability

高频：

- trace
- structured logs
- metrics
- latency
- token usage
- cost
- error type
- tool call trace
- replay
- alert
- dashboard
- OpenTelemetry
- Langfuse
- Prometheus
- Grafana
- Loki

当前项目：

- trace_id：有
- node latency：有
- model usage metadata：有
- tool step trace：新增
- full replay：无
- OTel：无
- centralized observability platform：无

---

# H. Security

高频：

- authentication
- authorization
- OAuth
- JWT
- RBAC
- ABAC
- tenant isolation
- prompt injection
- tool abuse
- tool permission
- secret isolation
- credential leakage
- sandbox
- file boundary
- risky action confirmation
- HITL
- audit

当前：

- API shared key：有
- admin key：有
- upload/path boundary：有
- prompt injection basic handling：有
- read-only MCP：有
- tool registry allowlist：新增
- tool arg validation：新增
- tool output untrusted rule：新增
- OAuth/JWT：无
- RBAC/ABAC：无
- multi-tenant：无
- sandbox：无
- approval gate：无

---

# I. Infra

进阶：

- Docker
- CI/CD
- Cloud
- Kubernetes
- Operator
- Terraform
- containerd
- gVisor
- Kata
- Firecracker
- Serverless
- distributed scheduler
- worker pool
- autoscaling
- HA
- sharding
- incident response

当前：

- Docker：有
- GitHub Actions：有
- K8s：无
- distributed worker：无
- IaC：无

对当前学生项目：

**先理解 > 盲目实现。**

---

# 5. 当前最值得升级的代码能力

## P0

### 1. Tool Agent 主链路整合

现在已有独立 bounded tool runtime。

下一步：

- 作为 LangGraph 节点集成
- 多工具
- 明确 read/write tool risk
- tool permission
- retry/fallback
- tool result citation

验收：

- 模型不能调用未注册工具
- 参数错误明确失败
- 工具超时不拖死请求
- trace 可定位每一步
- 有成功/失败回归集

---

### 2. Agent Eval

必须加入：

- task success rate
- tool selection accuracy
- argument validity
- recovery success
- step count
- latency
- cost

不再只测 retrieval。

---

### 3. Durable Task

目标不是马上上 Kafka。

先把任务模型搞对：

- queued
- running
- succeeded
- failed
- cancelled
- retrying

再考虑：

- persistent store
- worker
- lease
- retry
- resume

---

### 4. Async / concurrency / timeout

补：

- I/O concurrency
- bounded semaphore
- cancellation
- timeout budget
- tool timeout
- model timeout
- backend timeout

并做并发测试。

---

### 5. Context / Memory

先实现：

- token-aware context
- explicit memory interface
- short-term vs long-term separation

再考虑复杂 memory framework。

---

# P1

- Redis
- PostgreSQL
- durable queue
- JWT
- RBAC
- HITL
- model routing
- structured tool policy
- OpenTelemetry
- Langfuse
- cloud deploy
- rate limit
- circuit breaker

---

# P2

- Multi-Agent
- browser/computer use
- K8s
- sandbox virtualization
- distributed Agent Runtime
- large-scale scheduling

这些不是学生项目“必须全有”。

---

# 6. 技能入项目规则

以后任何技术走：

```text
招聘出现
→ 是否高频
→ 项目是否真的需要
→ 最小实验
→ 实现
→ 测试
→ 评测
→ 文档
→ 面试表达
```

统一状态：

- 已讲解
- 有 Demo
- 已实现
- 有测试
- 有效果证据
- 未实现

禁止：

```text
README 出现某词
= 已掌握
```

禁止：

```text
import langchain
= 会 Agent
```

---

# 7. 对求职的实际含义

如果目标是：

- Agent Backend
- AI Application
- LLM Application
- AI Full-stack 偏后端

建议学习权重：

```text
Python / CS / Backend          30%
RAG / Context                 20%
Agent / Tool / State          20%
Eval / Observability          15%
Reliability / Security        10%
Infra                         5%
```

这是学习优先级，不是企业统一评分公式。

如果投：

**Agent Infra**

则 Linux、Go、distributed system、K8s、queue、state machine、sandbox 权重会显著提高。

如果投：

**Agent Algorithm**

则 Transformer、PyTorch、RL、post-training、model eval、论文能力会显著提高。

本项目当前最匹配：

**Agent Backend / AI Application。**
