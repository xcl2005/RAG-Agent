# Roadmap

> 目标：
>
> 把项目从 Hybrid RAG 作品逐步升级成真正有求职价值的
> **Agent Backend / AI Application Engineering** 项目。
>
> 排序依据：
>
> **招聘频率 × 工程价值 × 当前项目契合度 × 学习收益 ÷ 复杂度**

# 0. 当前基线

已经有：

- Python
- FastAPI
- LangGraph
- Hybrid Retrieval
- SQLite FTS5
- Qdrant
- weighted RRF
- CrossEncoder rerank
- evidence gate
- context selection
- citation validation
- explicit abstention
- checkpoint
- SSE
- MCP
- Docker
- CI
- offline retrieval eval
- bounded Tool Agent runtime
- Tool Registry
- argument Schema
- tool timeout/error taxonomy
- tool execution trace

仍不能称：

- production Agent Runtime
- durable workflow platform
- multi-tenant AI platform

---

# P0：下一阶段必须优先

## P0.1 Tool Agent 集成主图

当前：

独立 `tooling.py` + CLI。

目标：

LangGraph 主链路可选择：

```text
answer via RAG
or
call registered tool
```

但仍有界。

需要：

- tool decision node
- tool execution node
- observation
- max step
- final answer
- error branch

验收：

- unknown tool 永远不执行
- schema invalid 不执行
- timeout 明确
- trace 完整
- 无无限循环

---

## P0.2 Tool Policy

增加 tool metadata：

- read/write
- risk
- timeout
- required permission
- confirmation required

先做：

只读 vs 写操作。

不要一开始上复杂 policy engine。

---

## P0.3 Agent Eval

新增：

```text
data/eval/agent/
```

至少：

- expected tool
- expected argument
- expected source
- should answer
- should abstain

指标：

- tool selection
- argument validity
- task success
- tool success
- steps
- latency

---

## P0.4 Full RAG Ablation

完成：

```text
Sparse
Dense
Hybrid
Hybrid+RRF
Hybrid+RRF+Rerank
```

同数据。

报告：

- Recall
- MRR
- nDCG
- false reject
- false allow
- latency

---

## P0.5 Token-aware Context

当前：

character budget。

升级：

- tokenizer
- prompt overhead
- evidence budget
- history budget
- tool observation budget

验收：

上下文总 token 不超设置。

---

## P0.6 Reliable Failure Model

统一错误：

```text
retrieval
model
citation
tool
timeout
permission
cancel
```

HTTP 和 UI 不显示一堆不同的模糊字符串。

---

## P0.7 Async / Cancellation

当前很多模型/检索逻辑仍是同步边界。

学习并逐步实现：

- cancellation
- overall deadline
- bounded concurrency
- backpressure

不要盲目把所有 def 改 async。

---

# P1：Agent Backend 工程化

## P1.1 Persistent Job State

当前：

JobRegistry 单进程内存。

第一步：

把 job metadata 持久化。

状态：

- queued
- running
- succeeded
- failed
- cancelled
- retrying

注意：

**持久 job metadata != durable execution。**

---

## P1.2 Worker / Durable Task

第二步：

把执行从 FastAPI process 解耦。

需要概念：

- worker
- lease
- heartbeat
- retry
- idempotency
- cancellation
- resume

技术再选择：

- Postgres
- Redis
- RQ/Arq/Celery
- Kafka

先设计语义。

---

## P1.3 PostgreSQL

把需要关系查询/任务状态/权限的数据逐步迁移到 Postgres。

不要为了关键词把全文检索和所有数据强行替换。

---

## P1.4 Redis

适合：

- cache
- rate limit
- ephemeral state
- distributed coordination

加入前先写：

具体使用场景。

---

## P1.5 Rate Limit

至少：

- per API key
- per IP 可选
- LLM request budget

学习：

- fixed window
- sliding window
- token bucket

---

## P1.6 Retry / Backoff

统一：

- retryable error
- non-retryable error
- exponential backoff
- jitter
- retry budget

工具与 LLM 分开。

---

## P1.7 HITL

高风险 tool：

```text
planned
→ pending approval
→ approved/rejected
→ execute
```

记录 audit。

---

## P1.8 Authentication / Authorization

顺序：

```text
shared key
→ JWT
→ user
→ role
→ resource permission
→ tool permission
```

不需要一开始上企业 SSO。

---

## P1.9 Memory

先定义 memory types。

实现顺序：

1. conversation state
2. summary memory
3. user preference memory
4. long-term semantic memory

需要：

- write criteria
- read criteria
- update
- delete
- privacy

---

## P1.10 Observability

先：

- structured trace
- tool spans
- model spans
- retrieval spans

再：

- OpenTelemetry
- Langfuse
- Prometheus/Grafana

---

# P2：进阶 Agent / Infra

## P2.1 Model Routing

根据：

- task
- cost
- latency
- capability

路由。

必须有 eval，不凭感觉。

---

## P2.2 Parallel Tool Calling

场景明确时：

并行读操作。

需要：

- concurrency limit
- partial failure
- merge
- timeout

---

## P2.3 Multi-Agent

只有单 Agent 明显不适合时才做。

评测问题：

多 Agent 是否真的：

- success ↑
- latency 可接受
- cost 可接受

否则不要加。

---

## P2.4 Sandbox

如果以后加入：

- code execution
- shell
- browser
- file write

才必须显著加强：

- process isolation
- filesystem
- network
- secret
- resource quota

---

## P2.5 Kubernetes

只有当项目开始：

- 多 worker
- horizontal scaling
- deployment

再学实现。

学生阶段：

理解 Deployment / Service / ConfigMap / Secret / HPA 已经有价值。

---

## P2.6 Resumable Streaming

Agent long-running 后：

客户端断开重连。

需要：

- persisted event offset
- execution state
- replay

---

# P3：研究/高级方向

- GraphRAG
- A2A
- large-scale multi-agent
- post-training
- SFT
- DPO/RL
- automated reasoning
- formal verification
- computer use
- multimodal RAG

是否做取决于岗位。

---

# 1. 招聘优先级与路线

## Agent Backend / AI Application

推荐：

```text
P0
→ P1 Tool/State/Queue/Eval
→ P1 Auth/Observability
→ 少量 P2
```

## Agent Infra

额外：

```text
Go
Linux
Distributed System
Queue
Postgres
Redis
K8s
Cloud
Sandbox
```

## Agent Algorithm

额外：

```text
PyTorch
Transformer
Post-training
RL
Model Eval
Paper
```

---

# 2. 每项功能完成定义

不能：

代码文件存在 = done。

至少分：

## Implemented

主代码存在。

## Tested

自动测试。

## Evaluated

效果测试。

## Documented

能解释。

## Operable

可以运行和排错。

招聘项目理想完成：

```text
Implemented
+ Tested
+ Evaluated
+ Documented
```

---

# 3. 不做什么

不要：

- 同时接 5 个 vector DB
- 同时接 5 个 agent framework
- 为了“微服务”把一个本地项目拆十个服务
- 没有并发需求就上 K8s
- 没有 write tool 就搭超复杂 sandbox
- 没有 eval 就声称 Agent 更聪明

---

# 4. 下一次 Codex 建议顺序

1. 运行全部测试，先修当前 Tool Runtime 的任何 CI 问题。
2. 把 Tool Runtime 集成 LangGraph。
3. 做 Agent eval dataset。
4. 做 RAG ablation。
5. persistent job state。
6. timeout/cancellation。
7. Redis/Postgres 按明确需求加入。
8. HITL + permission。
9. observability。
10. 再决定 multi-agent/K8s。

---

# 5. 每次升级的 commit 要回答

```text
Why?
What changed?
What can fail?
How tested?
What metric changed?
What remains unsupported?
```

这样项目升级记录本身就能成为面试材料。
