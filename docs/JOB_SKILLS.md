# Agent Backend / AI Application 招聘技能地图

> 更新：2026-09-06
>
> 目标岗位族：Agent Backend、AI 应用研发、大模型应用研发、LLM Application Engineer、AI 全栈、Agent Platform、Agent Runtime、Agent Infra、Applied AI / Forward Deployed、RAG / Search Agent、Agent Evaluation / Observability，以及用于对照的 Agent Algorithm / Research。
>
> **重要：本文件是“当前可追溯样本分析”，不是全互联网精确普查。** 招聘网站搜索、下线岗位、镜像收录和公司命名方式都会造成抽样偏差。比例只能用来判断方向，不能当官方市场份额。

# 0. 每次接手项目都必须先刷新招聘市场

根目录 `AGENTS.md` 已把这件事写成强制接手流程：

```text
读当前代码/文档/CI
→ 搜当期招聘
→ 按岗位族分类
→ 去重技能
→ 映射项目真实状态
→ 重排 Roadmap
→ 再开发
```

为什么必须重复做？因为 Agent 岗位变化速度快，2025 年常见的“RAG + LangChain”已经逐渐扩展为 2026 年的：

```text
Agent execution/runtime
+ Tool Calling / MCP / Skill
+ Context / Memory / State
+ Backend reliability
+ Eval / Observability
+ Permission / Security
+ Durable task / queue / worker
```

以后不能拿一次历史调研永久代表招聘市场。

---

# 1. 目前市场结构：不是“只有算法”，工程岗已经很大

## 1.1 本轮可追溯样本

本轮从 2026 年 7–9 月仍可检索的国内外岗位中，人工去重出 **25 个代表性技术岗位**。样本刻意覆盖不同公司和岗位族，而不是把同一公司几十个相似岗位全部重复计数。

分类规则：

- **应用/后端/全栈/Applied AI**：核心目标是把 LLM/Agent 接进真实产品或业务系统。
- **Runtime/Infra**：核心目标是 Agent 运行时、沙箱、队列、调度、云原生、权限、状态和平台底座。
- **算法/Research**：核心目标是模型训练、后训练、RL、Agent 算法、研究型能力优化。

样本结果：

| 岗位族 | 样本数 | 样本占比 | 对求职的含义 |
|---|---:|---:|---|
| AI Application / Agent Backend / AI Full-stack / Applied AI | 12 | **48%** | 当前最宽的 AI 落地工程入口 |
| Agent Runtime / Agent Infra / Systems | 5 | **20%** | 更偏 Go/C++/Linux/分布式/K8s，工程门槛更深 |
| Agent Algorithm / Post-training / Research | 8 | **32%** | 更常要求硕士及以上、PyTorch、RL/后训练，研究岗明显更难 |
| **工程类合计** | **17** | **68%** | 在这组 Agent/AI 相关技术岗里，约 2/3 是工程/系统路线 |

这不是“全行业 68%”的统计结论，而是**当前跨公司代表样本的结构**。但它足以说明一个重要事实：

> 对不走纯模型研究路线的人，Agent Backend / AI Application / Runtime 并不是边缘岗位，而是当前非常主流的一条 AI 技术就业路径。

## 1.2 对“要么后端，要么博士算法”的修正

这个判断有一半对：

- **纯前沿算法/研究岗确实门槛高。** Seed、快手 Agent 大模型算法、蚂蚁研究型岗位大量涉及 RL、SFT、DPO/PPO/GRPO、训练框架、论文/研究经历。
- **应用工程/Agent 后端明显更适合本科/硕士工程背景进入。** 很多岗位本科即可，重点看 Python/Java/Go、后端基础、Agent/RAG、工程交付和项目能力。

但不是简单二分，因为中间还有：

- AI Full-stack
- Applied AI / Forward Deployed
- Agent Evaluation Platform
- Data Agent
- Search / Knowledge Agent
- Agent Platform / Runtime
- AI Infra

这些岗位对学历要求和工程/算法权重都不同。

---

# 2. 代表性岗位证据

以下不是完整职位库，而是用于确定技能树和岗位边界的代表样本。

## 国内

### 百度：Agent 后端研发工程师

<https://talent.baidu.com/jobs/detail/SOCIAL/d1876313-6604-4e8d-bbcc-0dca5be4e51b>

关键词：Go、OS/网络/数据库、Agent 网关、Agent Harness、系统设计、测试、部署、运维。

### 百度：大模型应用研发工程师

<https://talent.baidu.com/jobs/detail/SOCIAL/a5ff8d15-b547-4a87-ba55-a128dae953cd>

关键词：Java/Python/Go、API/CLI/Skill、能力注册/治理/评估、Agent 工程框架、系统抽象、项目上下文。

### 百度：大模型研发校招

<https://talent.baidu.com/jobs/detail/GRADUATE/3b3888c3-5d8b-4c62-9bbb-a142c24e7d86>

本科起；Python、大模型 API、RAG、Agent、Prompt、推理服务、数据管道、Docker/K8s。

### 百度：云原生 Agent Infra

<https://talent.baidu.com/jobs/detail/SOCIAL/4b326f6b-2c39-461c-ae64-69b4201c680e>

关键词：Go/Python/C++、Linux、K8s/Operator、容器、分布式调度、sandbox、gateway、multi-tenant、MCP/Skill、可观测、自动恢复。

### 百度：大模型算法工程师

<https://talent.baidu.com/jobs/detail/SOCIAL/80dc23aa-5483-4272-afd6-851c58d107f3>

硕士及以上为主；Mid-training、SFT、RM、RL、PyTorch/深度学习、大模型优化。

### 字节 Seed

<https://seed.bytedance.com/zh/career>

当前可见 Code Agent、通用 Agent、强化学习、预训练等岗位。Seed 页面明显偏模型/算法研究团队，因此不能拿它代表字节全部 AI 应用工程岗位。

### 阿里：Agent Infra

<https://www.nowcoder.com/jobs/detail/439365>

本科起；高并发 Agent framework、sandbox、容器编排、任务调度、状态管理、checkpoint recovery、安全身份、SDK/API、观测。

### 阿里：Agent Infra OS

<https://www.nowcoder.com/jobs/detail/446392>

更偏 C++/OS、安全隔离、行为审计、Agent Runtime/OS 交互、可观测和效能优化。

### 京东：软件开发岗（AI 应用方向）

<https://zhaopin.jd.com/web/job-info-detail?requementId=220736>

关键词：Agent/Copilot/workflow、多步骤任务、planning、Tool Calling、routing、context、permission、fallback、RAG、eval、trace；同时明确 API、DB、cache、async task、microservice、container/cloud。

### 快手：Data Agent 研发

公开校招镜像可检索。关键词：Java/Spring、Multi-Agent、Skill、RAG、上下文压缩、Memory、评测/可观测、微服务、容器/沙箱。本科起。

### 快手：AI Agent 研发

公开社招镜像可检索。关键词：大模型业务应用、Agent 质量评估、评测框架、业务规模化落地。

### 快手：AI Agent 大模型算法

公开校招镜像可检索。关键词：Planning/Reasoning/Tool Use/Memory/RAG/Workflow/Multi-Agent、Agent Runtime、RL/SFT/DPO/PPO/GRPO、Benchmark/Trajectory。硕士及以上。

### 蚂蚁：AI 工程师

公开招聘镜像可检索。关键词：Context、RAG、Tool Calling、Memory、Eval、权限、索引、引用追踪、高并发、长任务、异步队列、cache、DB、降级恢复、observability。

### 蚂蚁：Agent / AI Infra 实习

<https://www.nowcoder.com/jobs/detail/442160>

本科可投；Agent planning、tool calling、memory、dialog management、reasoning engine、AI Infra、稳定性、端到端交付。

### 小红书：Agent 开发/引擎/产品研发

公开招聘镜像中可追溯到多组岗位，反复出现：ReAct、Tool Registry、argument validation、parallel tool、timeout/retry/fallback、trace/replay、token budget、context trimming、memory、sandbox、permission、HITL、resumable execution。

### 其他 AI 公司 / Startup

例如清昴 Agent 研发工程师公开校招信息已经直接写：Agent Harness、ReAct/Plan-and-Execute、Tool Calling、MCP、权限分级、调用链追踪、程序性/语义/情景记忆。说明这些能力已经不是只存在于大厂平台团队。

---

## 海外

### OpenAI：Software Engineer, API Agents

<https://openai.com/careers/software-engineer-api-agents-san-francisco/>

明确写这是 **software and systems engineering rather than model training**。

关键词：backend/infra、agent runtime、orchestration、search、execution environment、identity/permission、observability、eval、reliability、cost/latency、memory、tool execution、delegation、subagents/multi-agent。

### Anthropic：Applied AI Engineer

<https://job-boards.greenhouse.io/anthropic/jobs/5057647008>

关键词：production LLM、advanced prompting、Agent、evaluation、transcript analysis、MCP、deployment at scale、Python/TypeScript、production applications。

Anthropic 当前 Careers 页面同时显示大量 **Applied AI** 和 **AI Research & Engineering** 岗位，说明“应用工程”和“研究工程”已经是并列的大类，而不是只有研究岗。

### Anthropic：AI Engineer / GTM Claudification

公开职位强调：autonomous agents、approval/HITL、evaluation、production monitoring、MCP servers、skills、web apps、shared platform。

### Amazon AgentCore / LangChain Runtime

代表性要求高度集中于：long-running agent、durable execution、queue/worker、state persistence、resumable streaming、identity/isolation、observability、distributed systems、Postgres/Redis/K8s。

---

# 3. 技术要求频率评估

下面的百分比是对上述工程类代表样本做人工标签后的**近似区间**，避免职位写法不同造成“假精确”。

| 能力 | 工程类样本出现强度 | 结论 |
|---|---:|---|
| Python / Java / Go 至少一门主力语言 | **约 90%+** | 必须项；Python 最通用，Infra 更常见 Go/C++ |
| CS/Backend 基础：OS、网络、DB、API、系统设计 | **约 80–90%** | Agent 后端不是“会调模型 API”就够 |
| Agent workflow / tool calling / orchestration | **约 75–85%** | 当前核心能力 |
| RAG / retrieval / context engineering | **约 60–75%** | 仍然高频，但已经只是 Agent 系统的一部分 |
| 数据库 / cache / async task / queue | **约 50–70%** | 生产工程明显高频 |
| Evaluation / regression / failure analysis | **约 50–65%** | 2026 比传统 RAG 项目更重要 |
| Trace / observability / latency/cost | **约 45–60%** | Platform/Runtime 岗尤其高频 |
| State / checkpoint / memory | **约 40–55%** | 长任务与多轮 Agent 核心 |
| Docker / cloud / K8s | **约 40–55%** | 应用岗常是加分/部署能力，Infra 常是硬要求 |
| Permission / auth / sandbox / HITL | **约 30–45%** | 生产 Agent 比普通聊天应用更看重 |
| MCP / Skill / Plugin | **约 30–45%** | 快速上升，但不是每岗都点名 MCP |
| Multi-Agent | **约 20–35%** | 高频讨论项，但不是入门应用岗必需 |
| RL / SFT / post-training | 工程岗低；算法岗 **约 70–90%** | 不应为了投应用后端强行补成主项目 |

最重要的变化：

```text
2024/2025 常见：RAG + Prompt + LangChain

2026 更像：
Agent Runtime / Tool / Context / State
+ Backend / Queue / Cache / DB
+ Eval / Trace / Reliability
+ Security / Permission
+ RAG
```

---

# 4. 学历与进入难度

## 4.1 Agent Backend / AI Application

常见：本科及以上。

真正筛人的东西：

- 能否写可靠后端代码
- 数据结构/算法基本功
- API/DB/cache/concurrency
- 是否做过真实 RAG/Agent
- 能否解释失败、评测和 trade-off
- 项目是否能运行和测试

**这是当前本项目最现实的主目标。**

## 4.2 Agent Runtime / Infra

学历不一定比应用岗更高，但工程深度明显更高：

- Go/C++
- Linux/OS/network
- distributed systems
- queue/scheduler
- container/K8s
- sandbox/isolation
- HA/scaling

这条路不是“博士路线”，而是“系统工程路线”。

## 4.3 Agent Algorithm / Model / Research

算法工程常见硕士；顶级 Research/Scientist/前沿 RL/预训练更容易要求或偏好博士、顶会、强研究经历。

高频：

- PyTorch/JAX/TensorFlow
- Transformer
- SFT / preference optimization / RL
- data synthesis
- benchmark/eval
- training/inference systems
- paper/research ability

因此更准确的结论不是“算法岗一定博士”，而是：

> **纯模型算法/研究路线对普通本科/授课硕士求职者的进入门槛通常显著高于 Agent Backend / AI Application。**

---

# 5. 去重后的完整技能树 + 当前项目状态

状态词：`已实现`、`有测试`、`有效果证据`、`部分`、`未实现`。

## A. Programming / CS

需要学：Python、Go 基础、Java 基础、数据结构算法、OOP/设计模式、Linux、OS、Network、HTTP/TCP、SSE/WebSocket/RPC、Database fundamentals。

当前项目主要证明 Python；Go/Java 目前是学习路线，不应写成项目实现。

## B. Backend Engineering

| 技能 | 项目状态 |
|---|---|
| FastAPI / REST | 已实现 |
| SSE | 已实现节点级事件，不是逐 token streaming |
| SQLite | 已实现 |
| Qdrant | 已实现 |
| background ingestion | 已实现 |
| idempotent ingestion | 已实现 |
| timeout / failure classification | 部分 |
| Redis | 未实现 |
| PostgreSQL | 未实现 |
| Kafka/RabbitMQ | 未实现 |
| durable queue / worker | 未实现 |
| resumable long task | 未实现 |
| rate limiter | 未实现 |
| circuit breaker | 未实现 |
| distributed lock | 未实现 |

## C. RAG / Retrieval

| 技能 | 项目状态 |
|---|---|
| parsing / chunking / metadata | 已实现 |
| embedding / Qdrant | 已实现 |
| SQLite FTS5 sparse retrieval | 已实现 |
| hybrid retrieval | 已实现 |
| weighted RRF | 已实现 |
| reranker | 已实现 |
| multi-query planning | 已实现 |
| context selection | 已实现 |
| citation structure validation | 已实现 |
| evidence gate / refusal | 已实现 |
| retrieval eval | 部分，有离线实验 |
| final faithfulness eval | 不完整 |
| OCR / multimodal ingestion | 未实现 |

## D. Agent Core

| 技能 | 项目状态 | 代码证据 |
|---|---|---|
| bounded LangGraph workflow | 已实现 + 有测试 | `src/rag_agent/agent/graph.py` |
| state / SQLite checkpoint | 已实现 | LangGraph checkpoint |
| read-only MCP | 已实现 | `src/rag_agent/mcp/server.py` |
| Tool Registry | 已实现独立 runtime + 有测试 | `src/rag_agent/agent/tooling.py` |
| Tool schema / argument validation | 已实现 + 有测试 | Pydantic |
| tool timeout / error taxonomy | 已实现 + 有测试 | `tooling.py` |
| bounded tool loop | 已实现独立 runtime / Demo | `scripts/tool_agent.py` |
| knowledge search tool | 已实现只读 | Hybrid Retriever |
| parallel tools | 未实现 | - |
| generic retry/fallback policy | 不完整 | - |
| long-term memory | 未实现 | - |
| durable/resumable execution | 未实现 | - |
| HITL approval | 未实现 | - |
| multi-agent | 未实现 | - |
| sandbox | 未实现 | - |

**注意：独立 Tool Runtime 还没有并入主 RAG LangGraph。**

## E. Context / Memory

已有：history、checkpoint、context selection、character budget。

缺口：token-aware budget、summary memory、long-term memory、memory lifecycle/conflict/privacy。

## F. Evaluation

已有：unit test、retrieval/gate 基础评测、synthetic regression、Tool runtime behavior tests。

缺口：完整 task success、tool selection accuracy、argument accuracy、recovery success、real-model end-to-end、cost regression、online feedback。

## G. Observability

已有：trace ID、node latency、部分 model usage、tool step trace。

缺口：完整 replay、OpenTelemetry、Langfuse-class tracing、dashboard/alerts。

## H. Security

已有：shared API/admin key、upload/path boundary、基础 prompt-injection handling、read-only MCP、tool allowlist、arg validation。

缺口：OAuth/JWT、RBAC/ABAC、多租户、tool policy/approval、sandbox、audit trail。

## I. Infra

已有：Docker、GitHub Actions。

缺口：persistent worker、K8s、distributed scheduler、IaC、autoscaling。

---

# 6. 技术是否“全加进项目”应该怎么理解

如果“全加”指**所有招聘技术都写进代码**：没有，而且不应该这么做。

例如为了关键词同时加入 Kafka、RabbitMQ、Redis、Postgres、K8s、Multi-Agent、Firecracker，会得到一个难以解释、难以评测的技术拼盘。

正确目标是两层都“全”：

### 招聘覆盖要尽量全

所有高频能力进入本技能树，有来源、有优先级、有项目状态。

### 项目实现要选择性全

对 Agent Backend 最关键、最能形成完整工程故事的主链要逐步做完整：

```text
RAG
→ Tool Calling
→ Agent workflow/runtime
→ state/context/memory
→ eval
→ trace/observability
→ retry/recovery
→ durable task
→ permission/security
→ backend storage/cache/queue
→ deployment/scaling
```

不适合本项目的技术只学习或做小实验，不强行并入主系统。

---

# 7. 当前代码升级优先级

## P0

1. **把 Tool Runtime 并入 LangGraph 主链**：tool decision、execution、observation、bounded loop、error branch。
2. **Agent Eval**：task success、tool selection、argument validity、recovery、step count、latency、token/cost。
3. **完整 RAG ablation**：Sparse / Dense / Hybrid / RRF / Rerank 同数据对比。
4. **token-aware context**：history/evidence/tool observation 预算分开。
5. **统一 failure model + cancellation/deadline**。

## P1

1. persistent job state
2. worker / durable task
3. PostgreSQL
4. Redis
5. rate limit
6. retry/backoff
7. HITL
8. JWT/RBAC
9. explicit memory interface
10. OpenTelemetry/Langfuse-class observability

## P2

- model routing
- parallel tool calling
- multi-agent
- sandbox
- Kubernetes
- resumable streaming

P2 只有在 P0/P1 有真实需求和评测后再做。

---

# 8. 对求职的最终判断

如果目标是 2027 前后国内 AI 技术就业，本项目最合理的主定位仍然是：

1. **Agent Backend / 智能体后端**
2. **AI Application / 大模型应用研发**
3. **LLM Application Engineer**
4. **AI Full-stack（偏后端）**
5. **RAG / Search / Knowledge Agent**
6. **Agent Runtime / Infra（进阶）**

而不是用一个 API/RAG 项目硬包装成“模型算法工程师”。

学习权重建议：

```text
Python / CS / Backend          30%
RAG / Context                 18%
Agent / Tool / State          22%
Eval / Observability          15%
Reliability / Security        10%
Infra                          5%
```

如果专投 Agent Infra：把 Go/Linux/distributed/K8s/sandbox 权重显著提高。

如果专投 Agent Algorithm：另开 PyTorch/Transformer/post-training/RL/model-eval 学习线，不要假装当前应用项目能替代训练研究经历。