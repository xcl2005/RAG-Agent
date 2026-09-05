# Documentation

这个目录只保留少量长期维护的核心文档。

如果你第一次打开项目，不要从文件列表随机读。

> **当前招聘市场结论以 `JOB_SKILLS.md` 为准。** 招聘变化快，根目录 `AGENTS.md` 已要求每次 Codex/Agent 接手实质开发任务时先重新搜索当期招聘，再决定技术优先级。

## 阅读顺序

### 1. 主教材

**[LEARNING_GUIDE.md](LEARNING_GUIDE.md)**

这是唯一主要学习入口，目前为第二版“图解课程版”。

适合：

- 会基础 Python；
- 没系统学过 RAG / Agent；
- 后端知识不完整；
- 想知道每个模块为什么存在；
- 想把项目真正讲清楚。

主教材现在统一采用：

```text
为什么需要
→ 图解
→ 直觉例子
→ 原理
→ 项目真实代码
→ 跟做
→ 预期结果
→ 故意制造失败
→ 解释失败
→ 自己修改
→ 面试表达
```

并使用 `data/tutorial/expense_policy.md` 作为贯穿案例，从文档入库一路讲到 Hybrid RAG、LangGraph、Tool Agent、State/Checkpoint/Memory、Reliability、Security、Eval 与 Backend。

原则：**先教，再练，再复习；能跑不等于会，能改和能解释才接近掌握。**

### 2. 招聘技能地图

**[JOB_SKILLS.md](JOB_SKILLS.md)**

这是当前市场和技能优先级的权威文档，回答：

- Agent Backend / AI 应用现在到底招什么？
- 应用/后端、Runtime/Infra、算法/Research 的样本比例如何？
- 不同职位名称哪些能力其实相同？
- 本科/硕士/博士路线的进入门槛有什么区别？
- 当前项目已经覆盖多少？
- 哪些只是 Roadmap？
- 下一步为什么优先补某项？

当前代表性样本结论不是“官方市场份额”，而是跨公司可追溯样本分析；方法和边界都写在文档里。

### 3. 算法与 Coding

**[INTERVIEW_ALGORITHMS.md](INTERVIEW_ALGORITHMS.md)**

目前为第三版“图解训练版”。

完整目标：

```text
Hot100 主模式
+ 高频补充算法
+ ACM 输入输出
+ SQL
+ Backend Coding
+ CS 基础
+ System Design
+ RAG/Agent 项目深挖
+ AI Coding
```

它不再只是题号列表，而是把模式识别、Mermaid 图解、代码模板、工程迁移和面试变化题连起来。例如：

- Sliding Window → Rate Limiter
- Heap → TopK / Priority Task
- Topological Sort → Workflow DAG
- LRU → Cache
- Queue → Worker / Backpressure

并给出 P0/P1 题单、12 周训练计划和一周后复写的掌握标准。

### 4. 工程参考

**[ENGINEERING_REFERENCE.md](ENGINEERING_REFERENCE.md)**

需要查代码结构、数据流、SQLite/Qdrant 一致性、API/SSE、安全边界、MCP、Tool runtime、Docker/CI 和当前工程限制时再打开。

### 5. 评测

**[EVALUATION.md](EVALUATION.md)**

包含：

- 单元测试和效果评测区别；
- retrieval metrics；
- gate metrics；
- Agent/tool runtime 应该怎么评；
- 当前实验真实能证明什么；
- 下一步完整消融怎么做。

### 6. Roadmap

**[ROADMAP.md](ROADMAP.md)**

按 P0/P1/P2 排序，而不是堆 TODO。

---

## 每次接手项目的强制规则

见根目录 **[`AGENTS.md`](../AGENTS.md)**。

核心顺序：

```text
检查当前代码/CI
→ 搜索最新招聘
→ 岗位分类
→ 技能去重
→ 项目状态映射
→ Roadmap 重排
→ 再开发
```

这样项目不会因为一次旧调研长期偏离市场，也不会看到新技术名词就盲目加框架。

---

## 文档状态词

整个仓库统一使用：

- **已讲解**：文档有内容；
- **有 Demo**：存在最小可运行示例；
- **已实现**：已进入项目代码；
- **有测试**：存在自动测试；
- **有效果证据**：有可重复实验；
- **未实现**：只有知识/招聘记录/Roadmap。

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

旧版本有大量并列 Markdown：architecture、design、context engineering、tuning、security、evaluation、evaluation lab、interview、resume guide、learning path、hiring alignment、technology radar、experiment notes、code walkthrough。

现在收拢成：

```text
学习
招聘
面试
工程
评测
路线图
```

六个职责。Git 历史仍保留旧文件，需要追溯时可以从提交记录恢复，但它们不再作为日常入口。

---

## 给下一次 Codex / Agent 的文档维护规则

修改文档前先问：

1. 是否已经完成当期招聘扫描？
2. 这段内容应该进入现有哪个核心文档？
3. 是否真的需要新增 Markdown？
4. 技术是“讲解”还是“已实现”？
5. 是否有代码路径？
6. 是否有测试？
7. 是否有实验数据？
8. 是否会造成 README、主教材、招聘地图与真实代码状态不一致？
9. 新概念是否优先用图解 + 同一案例 + 实验，而不是只增加说明文字？

默认不要新增新的顶层 docs Markdown。
