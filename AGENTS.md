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

Update `docs/JOB_SKILLS.md` when material changes are found. Record source URL, date, company/role, level, education/experience, written skills, and role bucket.

Maintain a de-duplicated capability matrix covering programming/CS, backend, RAG/context, Agent, reliability/eval/observability/security, and infra.

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

The current textbook uses `data/tutorial/expense_policy.md` as a single fictional public case. Prefer extending that same case over unrelated examples.

Use GitHub-native Mermaid when it genuinely reduces cognitive load. Every major concept should move the learner through four levels: 看懂 → 能跑 → 能改 → 能独立实现.

---

## 5. Interview/algorithm rule

`docs/INTERVIEW_ALGORITHMS.md` must be a **self-contained textbook + problem book**, not a list of numbers or links.

It trains:

```text
Hot 100 patterns
+ company-frequency supplements
+ ACM input/output
+ SQL
+ backend hand-coding
+ CS fundamentals
+ system design
+ RAG/Agent deep dive
+ AI coding tasks
```

### 5.1 Review the user's starred algorithm repositories first

When local GitHub CLI/auth is available:

```bash
gh api --paginate user/starred --jq '.[].full_name'
```

Filter LeetCode / algorithms / interview / CodeTop / Hot100 / data-structures repos and record which materially influenced the curriculum. If star access is unavailable, say so explicitly.

Also compare high-quality public references such as:

- `labuladong/fucking-algorithm` — pattern-first reasoning and derivation.
- `doocs/leetcode` — breadth, topic indexing, per-problem lookup.
- `Hubert-hwk/hot100-judge` — Hot100 + CodeTop + ACM/core mode + tests.
- `leetcode-go/top-interview-150` — interview-oriented topic organization.

Reference structure, do not copy explanations or problem text.

### 5.2 Hot100 coverage and languages

The canonical target is **Hot100 100/100 coverage**. Every Hot100 problem retained in the canonical curriculum must eventually have both:

- complete Python solution
- complete Java solution

Hot100 is the foundation, not the whole interview syllabus. Keep company-frequency supplements, ACM, SQL, backend hand-coding, CS, system design and AI coding.

### 5.3 Every problem must teach the derivation, not just present an answer

A learner saying “I read the explanation but still could not derive it myself” means the explanation is insufficient.

For every canonical problem, use this teaching order:

```text
1. 题型 / 优先级 / 前置知识
2. 自写题意 + 原创例子
3. 第一反应：最直接的暴力解是什么？
4. 暴力解哪里慢 / 哪里重复？
5. 从例子中观察出什么规律？
6. 为什么这个规律允许换成当前数据结构/算法？
7. 核心不变量：循环过程中始终保证什么？
8. 手推一遍：至少 4–8 个关键状态变化
9. Python 完整代码
10. Python 逐段/关键行解释
11. Java 完整代码
12. Java 关键 API / 数据结构解释
13. 用同一个例子 dry-run 代码
14. 时间复杂度为什么是这个量级
15. 空间复杂度
16. 最常见错误：错误写法为什么错
17. 面试官改变条件后怎么重新推导
18. 同类题如何识别
19. Backend / Agent 工程迁移（适用时）
20. 一句话复述 + 闭卷重写验收
```

Do **not** jump from problem statement directly to the optimal trick. The derivation from brute force to optimization is the lesson.

For difficult concepts (DP, monotonic stack, graph, binary search boundaries, linked-list pointer rewiring), include a state table or Mermaid diagram when useful.

### 5.4 Readability and visual consistency are hard requirements

The textbook can be very long but must remain navigable:

```text
Top-level title
→ quick-start / legend / clickable index
→ Part
→ topic overview
→ one useful pattern diagram
→ collapsible problem cards
→ topic summary / transfer
→ review checklist
```

Rules:

- Use `<details><summary>...</summary>` for individual problems.
- One summary format: `LC 76 · Minimum Window Substring · Sliding Window · P0`.
- Keep fields in the same order for every problem.
- Avoid decorative noise, excessive emoji, duplicate diagrams and giant tables.
- Put code immediately beside the explanation it supports.
- End each topic with “这一类你应该会什么”.
- A learner should find any topic/problem in under 30 seconds.

### 5.5 Interview transfer

Explicitly connect algorithms to engineering where useful:

- Sliding Window → rate limiting
- Heap → TopK / priority tasks
- Topological Sort → workflow DAG
- LRU → caches
- Queue → workers/backpressure

Keep the set driven by current interview evidence, not arbitrary problem count.

---

## 6. Safety / repository hygiene

Never commit `.env`, API keys/tokens, private documents, user uploads, local databases/vector data, model caches, or personal data.

Do not rewrite stable code solely to look sophisticated. Handoffs must state exactly what remains unsupported.
