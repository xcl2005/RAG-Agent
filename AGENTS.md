# AGENTS.md — Project takeover protocol

This repository is both an engineering project and a long-term job-readiness learning project.
The hiring market changes faster than the codebase, so **every new Codex/Agent session that takes over meaningful project work must refresh the hiring market before choosing new technical priorities.**

## 0. Mandatory takeover order

1. Read `README.md`, `docs/README.md`, `docs/JOB_SKILLS.md`, `docs/ROADMAP.md`, then inspect the relevant code/tests.
2. Check current branch/HEAD and CI/test state. Never trust an old handoff sentence as proof that the current commit is green.
3. Search current hiring requirements on the web. Do not answer from model memory alone.
4. Search multiple role names because the same work is advertised under different titles.
5. De-duplicate requirements into capabilities rather than framework/vendor names.
6. Compare those capabilities with the repository's real implementation state.
7. Re-rank the roadmap using current hiring frequency × engineering value × project fit × learning value ÷ complexity.
8. Only then implement features. Update docs/status before handoff when the market or implementation state changed materially.

If web access is unavailable, explicitly record that the hiring refresh could not be completed. Never invent a current market view.

---

## 1. Hiring scan scope

Search at least these role families:

- Agent Backend / 智能体后端
- AI Application Engineer / AI 应用研发
- 大模型应用研发 / LLM Application Engineer
- AI Full-stack（偏后端）
- Agent Platform / Runtime / Harness
- Agent Infra / AI Infra
- Applied AI / Forward Deployed / Deployed Engineer
- RAG / Knowledge / Search Agent engineering
- Agent evaluation / observability platform
- Agent algorithm / post-training / research roles, for comparison

Do not mix algorithm/research and application/backend into one bucket just because both contain `Agent`.

Prioritize official sources. China: Baidu, ByteDance/Seed, Alibaba/Alibaba Cloud, Tencent, Meituan, JD, Xiaohongshu, Kuaishou, Ant, Huawei, Xiaomi, major AI startups. Global: OpenAI, Anthropic, Amazon/AWS, Google, Microsoft, Meta, Databricks, LangChain/LangSmith and representative Applied-AI/Agent companies.

Sample internship/graduate roles separately from experienced-hire roles.

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

Use this pipeline:

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

## 4. Main learning guide rule

`docs/LEARNING_GUIDE.md` is the main textbook. Keep it large, coherent and beginner-readable rather than splitting every topic into many Markdown files.

The learner knows basic Python but may know almost nothing about RAG, Agent, backend reliability or evaluation.

### 4.1 Teach from a concrete problem, not from architecture jargon

For every major concept, prefer this order:

```text
real problem
→ concrete input/output example
→ what goes wrong with the naive approach
→ intuition
→ step-by-step data changes
→ principle
→ repository code path
→ run it
→ expected result
→ deliberately break it
→ explain the failure
→ modify one variable
→ interview explanation
```

The current textbook uses `data/tutorial/expense_policy.md` as the single running case. Prefer extending that case.

### 4.2 Visual teaching must be reader-friendly

Do **not** treat Mermaid/ASCII flowcharts as the default teaching method. A learner should not need to mentally compile diagram syntax.

Preferred order:

1. normal Chinese explanation;
2. small tables showing inputs, intermediate states and outputs;
3. numbered step cards;
4. short code snippets only when teaching actual code;
5. repository-local PNG/SVG illustrations only when a real visual materially improves understanding.

Rules:

- Mermaid may be used only sparingly when GitHub rendering clearly improves understanding; it must never be the only explanation.
- Do not use ASCII diagrams as primary teaching content.
- Do not hotlink decorative diagrams/images from external sites.
- If a static figure is useful, store it under `docs/assets/` and keep the figure simple, labeled in Chinese, and tied to this repository.
- Do not put a large architecture picture before explaining what problem each component solves.
- A diagram must be understandable even if the reader ignores all implementation details.

### 4.3 Four learning levels

Every major topic should move the learner through:

1. `看懂` — explain it in their own words.
2. `能跑` — reproduce a real repository path/test/CLI.
3. `能改` — change a parameter/implementation and explain the effect.
4. `能独立实现` — build a small version from a blank file.

Teach first; practice second; quiz last.

---

## 5. Interview/algorithm rule

`docs/INTERVIEW_ALGORITHMS.md` must be a self-contained textbook + problem book, not a number/link list.

It trains:

```text
Hot100
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

Also compare public references such as:

- `labuladong/fucking-algorithm` — pattern-first reasoning and derivation.
- `doocs/leetcode` — breadth and topic indexing.
- `Hubert-hwk/hot100-judge` — Hot100 + CodeTop + ACM/core mode + tests.
- `leetcode-go/top-interview-150` — interview-oriented topic organization.

Reference structure, do not copy explanations/problem text.

### 5.2 Hot100 coverage and languages

Canonical target: **Hot100 100/100 coverage**.

Every canonical Hot100 problem must contain both:

- complete Python solution;
- complete Java solution.

Hot100 is the foundation, not the whole interview syllabus. Keep company-frequency supplements, ACM, SQL, backend coding, CS, system design and AI coding.

### 5.3 Every problem must teach derivation

If a learner says “I read the explanation but still could not derive it myself,” the explanation is insufficient.

Use this order for every canonical problem:

```text
1. 题型 / 优先级 / 前置知识
2. 自写题意 + 原创例子
3. 第一反应：暴力解是什么
4. 暴力解哪里慢/重复
5. 从例子观察到什么规律
6. 为什么这个规律允许当前算法
7. 核心不变量
8. 手推至少 4–8 个关键状态
9. Python 完整代码
10. Python 关键行解释
11. Java 完整代码
12. Java 数据结构/API解释
13. 同一例子 dry-run
14. 时间复杂度为什么
15. 空间复杂度
16. 常见错误以及为什么错
17. 改条件后如何重新推导
18. 同类题识别信号
19. Backend/Agent 迁移（适用时）
20. 一句话复述 + 闭卷重写验收
```

Do not jump from statement directly to an optimal trick.

### 5.4 Algorithm-document readability

The document can be huge but must remain navigable:

```text
quick-start / legend / clickable index
→ Part
→ topic overview
→ plain-language pattern explanation
→ collapsible problem cards
→ topic summary / engineering transfer
→ review checklist
```

Rules:

- Use `<details><summary>...</summary>` for individual problems.
- One summary format: `LC 76 · Minimum Window Substring · Sliding Window · P0`.
- Keep fields in the same order.
- Avoid excessive emoji, decorative badges, giant tables and diagram spam.
- Prefer state tables/dry-runs to flowchart code.
- End each topic with `这一类你应该会什么`.
- A learner should find any topic/problem in under 30 seconds.

Explicitly connect algorithms to engineering when useful: Sliding Window→rate limiting, Heap→TopK/priority tasks, Topological Sort→workflow DAG, LRU→cache, Queue→workers/backpressure.

---

## 6. Safety / repository hygiene

Never commit `.env`, API keys/tokens, private documents, user uploads, local databases/vector data, model caches, or personal data.

Do not rewrite stable code solely to look sophisticated. Handoffs must state exactly what remains unsupported.
