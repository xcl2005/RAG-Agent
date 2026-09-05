# 招聘要求与本轮升级：2026-09

核验日期：2026-09-05。暂按 **实习 / 初级 AI 应用工程师（Agent、RAG）** 定位，适合目前能写基础 Python、但还不能完整解释项目的学习起点。它不是模型训练 / 算法研究岗位的替代准备。

## 1. 先看真实岗位，不根据热词堆框架

以下是定向读取的官方样本，国内可完整读取的 JD 偏百度，不能据此推断全国招聘占比。发布日期与访问日期分开列出；无发布日期不代表刚发布。

| 官方来源 | 页面发布日期 | 与本项目有关的要求 |
|---|---|---|
| [百度：智能体应用开发实习生 J99649](https://talent.baidu.com/jobs/detail/INTERN/e3cec5b8-b7a3-4946-99fc-b292b749cd53) | 2026-07-21 | Python / Java / Go，操作系统、算法、网络，RAG、Prompt、Agent 编排，文档与独立分析。最接近当前目标。 |
| [百度：大模型应用/agent 算法实习 J101345](https://talent.baidu.com/jobs/detail/INTERN/1a0bfe96-f59c-4384-9525-79fdf324c67f) | 2026-07-21 | 规划、检索、生成的评估→优化→验证；另要求硕士、PyTorch、Transformer、后训练基础，不能只靠本项目覆盖。 |
| [百度：Agent 算法实习生 J97505](https://talent.baidu.com/jobs/detail/INTERN/cd423c1c-7a35-4672-b0a7-2857308efe43) | 2026-07-21 | Python、系统实现、生成/评价/改进循环、稳定性与推理效率。 |
| [字节 Seed：2027 届人才校招方向](https://seed.bytedance.com/zh/seedearlycareer) | 未显示 | 应用方向含搜索理解、Search Agent、记忆、反馈；强调代表性工作与动手能力。是研究校招方向页，非普通应届统一门槛。 |
| [Anthropic：Applied AI Engineer, Enterprise Tech](https://job-boards.greenhouse.io/anthropic/jobs/5057647008) | 未显示 | Agent、评测、运行记录分析、MCP、部署与沟通；要求 4+ 年经验，仅作进阶参照。 |

我的选型判断：RAG 和 Workflow 没有被替代；新要求更多是在问“你怎样证明有效、定位失败、控制成本与权限”。单人作品集应优先拿出可复现实验和代码证据。

## 2. 技术变化怎样落到代码

| 能力 | 本轮交付 | 可以怎样证明 | 仍然不能声称 |
|---|---|---|---|
| Context engineering | `prepare_context` 节点：同源去重、清单问题跨来源排序、精确字符预算、可见原文一致性 | 运行 `tests/test_prompts.py`，看 trace 的裁剪/去重统计 | token 精确控制、语义压缩、自动事实核验 |
| Evaluation-driven development | 独立临时 SQLite、公开虚构语料、sparse 与术语扩展对照、逐题失败记录 | `scripts/eval_portfolio.py`，保留数据哈希、参数、Git 状态和原始报告 | dense/LLM 的线上准确率、客户效果、行业 benchmark 排名 |
| 故障可解释性 | 保留证据不足 / 模型生成失败 / 引用失败分类；新增上下文节点 | 单元测试、SSE 与 API trace | 完整 OpenTelemetry 平台或自动故障恢复产品 |
| 个人理解与表达 | 练习 CLI、14 天阅读路线、手写实验与自评 | 先答再揭示解析，展示自己的实验笔记与变更 | 读完文档就已熟练、所有模块均独立原创 |

技术参考不是“必须照搬”：

- [Anthropic：Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)，2025-09-29 发布：强调上下文是有限资源。这里采用可解释的确定性选择，没有引入额外摘要模型。
- [Anthropic：Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)，2026-01-09 发布：用清晰任务与可核验评分发现回归，兼顾应该与不应该发生的行为。这里同时报告误拒答与错误放行，不只挑正面数字。
- [Anthropic：Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents)，2026-04-08 发布：长任务关注会话、执行环境、运行控制与恢复。当前本地应用只借鉴边界与故障解释，不假装已经建成托管 Agent 平台。

## 3. 哪些暂时不加，为什么

- 不叠加第二套 Agent 框架。一个 LangGraph 已能表达这条有界流程；解释状态和失败路径比多写 SDK 名字更重要。
- 不先上多 Agent、A2A、GraphRAG。尚无独立协作角色、跨组织协议或关系多跳评测证明它们有收益。
- 不把共享密钥包装成 RBAC，不把内存 JobRegistry 包装成持久化队列。不把 SQLite 的本地功能测试当万人并发验证。
- 不用 LLM judge 给自己打高分。先跑确定性检索评测；逐句引用是否支持答案，需要后续人工标注和校准。
- 不为了“最新”盲升所有依赖大版本。已有接口、版本上界与 CI 是真实约束。

## 4. 什么才算变成“我的项目”

你需要能画出一次请求的路径、定位一个真实失败、亲手做一次改动并解释代价。保留 AI 辅助开发的事实；简历只写已掌握和实际完成的部分，不伪造提交历史、生产用户、性能提升或独立原创经历。

从 [学习路线](learning-path.md) 第一天开始。先用自己的话回答“为什么模型不能直接读完整个资料库”，再运行上下文预算测试。暂时答不出来，是下一步要学的具体内容，不需要包装。
