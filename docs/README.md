# Documentation

这个目录只保留少量长期维护的核心文档。

如果你第一次打开项目，不要从文件列表随机读。

> **当前招聘市场结论以 `JOB_SKILLS.md` 为准。** 招聘变化快，根目录 `AGENTS.md` 已要求每次 Codex/Agent 接手实质开发任务时先重新搜索当期招聘，再决定技术优先级。

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
→ 项目真实代码
→ 跟做
→ 观察结果
→ 修改实验
→ Trade-off
→ 面试表达
```

原则：**先教，再练，再复习。**

主教材负责知识与项目理解；其中若出现历史招聘描述，应以最新 `JOB_SKILLS.md` 的市场扫描覆盖它，不要把历史样本当永久结论。

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

第二版已经不是简单题目列表。

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

文档包含明确题号/P0/P1、12 周学习路线、工程迁移和掌握标准。

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

旧版本有大量并列 Markdown：architecture、design、context engineering、tuning、security、evaluation、evaluation lab、interview、resume guide、learning path、hiring alignment、technology radar、experiment notes、code walkthrough。

它们很多内容重复，而且学习者很难判断先读谁。

现在按：

```text
学习
招聘
面试
工程
评测
路线图
```

六个职责收拢。

Git 历史仍保留旧文件，所以需要追溯时可以从提交记录恢复，但它们不再作为日常入口。

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

默认不要新增新的顶层 docs Markdown。