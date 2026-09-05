# Documentation

这个目录只保留少量长期维护的核心文档。

如果你第一次打开项目，不要从文件列表随机读。

## 阅读顺序

### 1. 主教材

**[LEARNING_GUIDE.md](LEARNING_GUIDE.md)**

这是唯一主要学习入口。

适合：

- 会基础 Python
- 没系统学过 RAG / Agent
- 后端知识不完整
- 想知道每个模块为什么存在
- 想把项目真正讲清楚

学习方式：

```text
问题
→ 直觉
→ 原理
→ 例子
→ 项目代码
→ 跟做
→ 观察结果
→ 修改实验
→ Trade-off
→ 面试表达
```

不要“没教先考”。

### 2. 招聘技能地图

**[JOB_SKILLS.md](JOB_SKILLS.md)**

回答：

- Agent Backend / AI 应用现在到底招什么？
- 不同职位名称哪些能力其实相同？
- 国内大厂和海外 Agent 平台团队反复要求什么？
- 当前项目已经覆盖多少？
- 哪些只是 Roadmap？
- 下一步为什么优先补某项？

### 3. 算法与 Coding

**[INTERVIEW_ALGORITHMS.md](INTERVIEW_ALGORITHMS.md)**

Hot100 是主干，但不是完整面试。

完整目标：

```text
Hot100
+ 高频补充算法
+ SQL
+ Backend Coding
+ CS 基础
+ System Design
+ RAG/Agent 项目深挖
+ AI Coding
```

### 4. 工程参考

**[ENGINEERING_REFERENCE.md](ENGINEERING_REFERENCE.md)**

需要查：

- 代码结构
- 数据流
- SQLite/Qdrant 一致性
- API/SSE
- 安全边界
- MCP
- Tool runtime
- Docker/CI
- 当前工程限制

时再打开。

### 5. 评测

**[EVALUATION.md](EVALUATION.md)**

包含：

- 单元测试和效果评测区别
- retrieval metrics
- gate metrics
- Agent/tool runtime 应该怎么评
- 当前实验真实能证明什么
- 下一步完整消融怎么做

### 6. Roadmap

**[ROADMAP.md](ROADMAP.md)**

按 P0/P1/P2 排序，而不是堆 TODO。

---

## 文档状态词

整个仓库统一使用：

- **已讲解**：文档有内容
- **有 Demo**：存在最小可运行示例
- **已实现**：已进入项目代码
- **有测试**：存在自动测试
- **有效果证据**：有可重复实验
- **未实现**：只有知识/招聘记录/Roadmap

这些词不能互相替代。

例如：

> `Tool Registry` 已实现且有测试。

不代表：

> 主 RAG 图已经是完整生产 Tool-Calling Agent。

同样：

> 文档讲了 Redis。

不代表：

> 项目已经接入 Redis。

---

## 当前文档结构为什么这样整理

旧版本有大量并列 Markdown：

- architecture
- design
- context engineering
- tuning
- security
- evaluation
- evaluation lab
- interview
- resume guide
- learning path
- hiring alignment
- technology radar
- experiment notes
- code walkthrough

它们很多内容重复，而且学习者很难判断先读谁。

现在按“学习、招聘、面试、工程、评测、路线图”六个职责收拢。

Git 历史仍保留旧文件，所以以后需要追溯历史说明时可以从提交记录恢复，
但它们不再作为日常入口。

---

## 给下一次 Codex / Agent 的维护规则

修改文档前先问：

1. 这段内容应该进入现有哪个核心文档？
2. 是否真的需要新增 Markdown？
3. 技术是“讲解”还是“已实现”？
4. 是否有代码路径？
5. 是否有测试？
6. 是否有实验数据？
7. 是否会造成 README 与真实状态不一致？

默认不要新增新的顶层 docs Markdown。
