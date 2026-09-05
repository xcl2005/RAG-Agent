# AGENTS.md — Project takeover protocol

This repository is both an engineering project and a long-term job-readiness learning project.
The hiring market changes faster than the codebase, so **every new Codex/Agent session that takes over meaningful project work must refresh the hiring market before choosing new technical priorities.**

## 0. Mandatory takeover order

1. Read `README.md`, `docs/README.md`, `docs/JOB_SKILLS.md`, `docs/ROADMAP.md`, then inspect the relevant code/tests.
2. Check the current branch/HEAD and CI/test state. Never trust an old handoff sentence as proof that the current commit is green.
3. **Search current hiring requirements on the web.** Do not answer from model memory alone.
4. Search multiple role names because the same work is advertised under different titles.
5. De-duplicate requirements into capabilities rather than counting framework/vendor names.
6. Compare those capabilities with the repository's real implementation state.
7. Re-rank the roadmap using current hiring frequency × engineering value × project fit × learning value ÷ complexity.
8. Only then implement features. Update docs/status before handoff if the market or implementation state changed materially.

If web access is unavailable, explicitly record that the hiring refresh could not be completed. Never invent a current market view.

---

## 1. Hiring scan scope

Search a broad set of role families, including at least:

- Agent Backend / 智能体后端
- AI Application Engineer / AI 应用研发
- 大模型应用研发 / LLM Application Engineer
- AI Full-stack（偏后端）
- Agent Platform / Agent Runtime / Agent Harness
- Agent Infra / AI Infra
- Applied AI / Forward Deployed / Deployed Engineer
- RAG / Knowledge / Search Agent engineering
- Agent evaluation / observability platform
- Agent algorithm / post-training / research roles, for comparison

Do not mix algorithm/research and application/backend into one bucket just because both contain the word `Agent`.

### Companies / ecosystems to refresh

Prioritize official sources; use clearly labeled mirrors only when official detail pages are inaccessible.

China: Baidu, ByteDance/Seed, Alibaba/Alibaba Cloud, Tencent, Meituan, JD, Xiaohongshu, Kuaishou, Ant, Huawei, Xiaomi, major AI startups.

Global: OpenAI, Anthropic, Amazon/AWS, Google, Microsoft, Meta, Databricks, LangChain/LangSmith and representative Applied-AI/Agent companies.

Also sample current internship/graduate roles separately from experienced-hire roles. Do not apply a staff-level requirement to a student role.

---

## 2. Required hiring-scan output

Update `docs/JOB_SKILLS.md` when material changes are found. Record:

- source URL
- access/update date when available
- company and role family
- internship / graduate / experienced hire
- minimum education / experience when stated
- skills actually written in the posting
- role bucket: application/backend, runtime/infra, full-stack/applied, algorithm/research

Then maintain a de-duplicated capability matrix. At minimum cover:

### Programming / CS
Python, Go, Java, C/C++, data structures, algorithms, OS, networking, Linux, databases, system design.

### Backend
API, FastAPI/Spring/Node where relevant, async/concurrency, SSE/WebSocket/RPC, SQL/PostgreSQL/MySQL, Redis/cache, MQ/worker/task queue, idempotency, retry, timeout, rate limit, fallback/circuit breaker, high availability, high concurrency, microservices/distributed systems.

### RAG / Context
parsing, chunking, embedding, sparse/dense/hybrid retrieval, RRF, reranking, query rewrite, metadata, context selection/compression, grounding, citation, refusal, retrieval/end-to-end evaluation.

### Agent
Tool/Function Calling, Tool Registry, schema/argument validation, ReAct/planning/workflow, state/checkpoint, context engineering, memory, model routing, MCP/Skill/Plugin, long-running/durable execution, parallel tools, multi-agent, HITL.

### Reliability / Evaluation / Observability / Security
structured output, failure taxonomy, retry/recovery, task/tool success, regression eval, trace/log/metrics, latency/token/cost, OpenTelemetry/Langfuse-class tooling, auth/permission, prompt injection, tool abuse, audit, sandbox/isolation.

### Infra
Docker, CI/CD, cloud, Kubernetes, worker/scheduler, autoscaling, distributed runtime, sandbox/container isolation.

---

## 3. Never confuse market coverage with code coverage

Every capability uses these states:

- `已讲解`
- `有 Demo`
- `已实现`
- `有测试`
- `有效果证据`
- `未实现 / Roadmap`

A skill appearing in a JD or document does **not** mean it has been implemented.

Before changing README/project claims, verify code path + tests + evaluation evidence.

Recommended pipeline:

```text
fresh hiring evidence
→ de-duplicate capability
→ estimate importance/frequency
→ map repository status
→ decide whether the project genuinely needs it
→ smallest useful implementation
→ tests
→ evaluation
→ learning documentation
→ interview explanation
```

Do not install frameworks merely to increase keyword count.

---

## 4. Learning-document rule

`docs/LEARNING_GUIDE.md` is the main textbook. Keep it large, coherent and beginner-readable rather than splitting every topic into a new Markdown file.

Teach in this order:

```text
why the problem exists
→ visual model / diagram
→ intuition
→ principle
→ small example
→ real repository code
→ run it
→ expected result
→ deliberately break it
→ explain the failure
→ modify one variable
→ trade-off
→ why hiring interviews care
→ how to explain it
```

The current textbook uses `data/tutorial/expense_policy.md` as a single fictional public case. Prefer extending that same case over inventing unrelated examples in every chapter.

### Visual pedagogy is a requirement, not decoration

Use GitHub-native Mermaid when a concept benefits from structure or flow. Prefer diagrams for:

- RAG ingestion/retrieval/generation flow
- sparse vs dense vs fusion vs rerank
- LangGraph state transitions
- Tool Calling / Registry / validation / timeout
- State vs Checkpoint vs History vs Memory vs Context
- API/SSE request lifecycle
- queue/worker/durable task
- retry/deadline/failure paths
- permission/HITL/sandbox boundaries
- eval/trace/observability
- backend system design

Do not copy diagrams or images from external tutorials. Learn from good official explanations, then redraw concepts around this repository.

Every major concept should move the learner through four levels:

1. `看懂` — explain it in their own words.
2. `能跑` — reproduce a real repository path/test/CLI.
3. `能改` — change a parameter or implementation and explain the effect.
4. `能独立实现` — build a small version from a blank file.

Teach first; practice second; test/quiz last. Never use an unimplemented capability as if the project already supports it.

---

## 5. Interview/algorithm rule

`docs/INTERVIEW_ALGORITHMS.md` is not a list of links. It should train the complete interview stack for Agent Backend / AI Application roles:

```text
Hot 100 patterns
+ company-frequency algorithm supplements
+ ACM input/output
+ SQL
+ backend hand-coding
+ CS fundamentals
+ system design
+ RAG/Agent deep dive
+ AI coding tasks
```

For each algorithm family, prefer:

```text
recognition signal
→ visual model
→ core invariant
→ template
→ representative problems
→ common mistakes
→ complexity
→ variant
→ backend/Agent transfer
→ spaced re-write standard
```

Explicitly connect algorithms to engineering where useful, for example:

- Sliding Window → rate limiting
- Heap → TopK / priority tasks
- Topological Sort → workflow DAG
- LRU → caches
- Queue → workers/backpressure

Keep the question set driven by current interview evidence, not by arbitrary total problem count.

---

## 6. Safety / repository hygiene

Never commit `.env`, API keys/tokens, private documents, user uploads, local databases/vector data, model caches, or other personal data.

Do not rewrite stable code solely to look more sophisticated. When handing off, state exactly what remains unsupported.
