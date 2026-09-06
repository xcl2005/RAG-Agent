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

`docs/INTERVIEW_ALGORITHMS.md` must be a **self-contained textbook + problem book**, not merely a list of LeetCode numbers or external links.

It should train the complete interview stack for Agent Backend / AI Application roles:

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

### 5.1 Review the user's starred algorithm repositories first

When local GitHub CLI/auth is available, inspect the authenticated user's starred repositories before changing the algorithm curriculum:

```bash
gh api --paginate user/starred --jq '.[].full_name'
```

Filter for LeetCode / algorithms / interview / CodeTop / Hot100 / data-structures repositories and record which ones materially influenced the curriculum. If `gh` or star access is unavailable, state that explicitly instead of pretending the starred list was reviewed.

Also refresh high-quality public references. Current examples worth comparing include:

- `labuladong/fucking-algorithm` — pattern-first reasoning, visual explanation, spaced practice.
- `doocs/leetcode` — broad coverage, topic indexing, searchable per-problem explanations.
- `Hubert-hwk/hot100-judge` — Hot100 + CodeTop frequency, ACM/core-code dual mode, local tests/progress.
- `leetcode-go/top-interview-150` — topic-based interview organization.

These are **reference designs**, not sources to copy. Paraphrase problem statements, write original explanations/code/examples, and keep attribution/links where a reference materially influenced structure.

### 5.2 Every included algorithm problem must be self-contained

For every problem retained in the study route, include inside the document:

```text
problem number/title + type/pattern + priority
→ original paraphrased task description (not copied LeetCode text)
→ small original example
→ recognition signals
→ brute-force baseline when educationally useful
→ optimal idea / invariant
→ diagram when useful
→ complete Python solution
→ time/space complexity
→ common mistakes
→ at least one variant/follow-up
→ backend/Agent transfer when relevant
→ review checkpoint
```

A learner should not need to open LeetCode to understand the task or solution. External links are optional verification/reference only.

### 5.3 Readability and visual consistency are hard requirements

The algorithm textbook can be very long, but it must never look like an unstructured Markdown dump.

Use one stable page hierarchy:

```text
Top-level title
→ quick-start / legend / table of contents
→ Part
→ topic overview
→ one pattern diagram
→ collapsible problem cards
→ topic summary / transfer
→ review checklist
```

Formatting rules:

- Keep a clickable table of contents or compact topic index near the top.
- Move reference-source notes and maintenance details to an appendix; do not put them before the actual learning path.
- Use `<details><summary>...</summary>` for individual problem solutions so 50–100+ problems remain browsable.
- Every problem summary uses one format, e.g. `LC 76 · Minimum Window Substring · Sliding Window · P0`.
- Use `P0 / P1 / P2` consistently; define the legend once instead of explaining it repeatedly.
- Put `题意 / 例子 / 识别 / 思路 / 代码 / 复杂度 / 易错 / 追问 / 工程迁移` in the same order for every problem.
- Avoid excessive emoji, decorative badges, nested heading noise and giant unbroken tables.
- Prefer short paragraphs, small tables and Mermaid only when they reduce cognitive load.
- Do not show multiple similar diagrams for the same pattern; one good diagram is better than decoration.
- Keep code blocks immediately next to the explanation they support.
- At the end of each topic, include a compact “这一类你应该会什么” checklist.
- Maintain enough whitespace between cards/sections so GitHub rendering is comfortable on desktop and mobile.

Before handoff, visually inspect the rendered Markdown on GitHub when possible. The acceptance question is not only “is the content complete?” but also “can a learner find the right topic/problem in under 30 seconds?”

For each algorithm family, prefer:

```text
recognition signal
→ visual model
→ core invariant
→ template
→ fully explained representative problems
→ common mistakes
→ complexity
→ variants
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
