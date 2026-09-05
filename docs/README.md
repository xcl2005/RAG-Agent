# 文档导航

> 当前状态：文档体系重构第 1 阶段。旧文档暂时保留，避免在迁移完成前丢失独有内容。后续会把重复内容迁入下列核心文档，再删除过时文件。

这个目录以后只保留少量、职责明确的核心入口。**文档数量要少，但教材本身可以很长。**

## 先看哪一份

如果你的目标是从零理解项目并能够自己修改、解释和面试，当前先读：

1. [`PROJECT_HANDBOOK.md`](PROJECT_HANDBOOK.md) —— 当前主教材。已经覆盖项目原理、真实代码、跟做、评测和求职表达；后续会继续扩写并最终迁移/重命名为长期 `LEARNING_GUIDE`。
2. [`INTERVIEW_ALGORITHMS.md`](INTERVIEW_ALGORITHMS.md) —— 算法、SQL、Backend Coding 与 AI Coding 学习路线。Hot 100 是主干，不是全部。
3. [`JOB_SKILLS.md`](JOB_SKILLS.md) —— Agent Backend / AI Application / LLM Engineering 等岗位的招聘技能矩阵和项目差距。

如果你只是开发或排错，再按需查参考文档，不需要从头读完所有旧 Markdown。

## 目标文档结构

| 文档 | 长期职责 | 当前状态 |
|---|---|---|
| `PROJECT_HANDBOOK.md` / 未来 `LEARNING_GUIDE.md` | 从 0 开始的主教材：RAG → Agent → Backend → Evaluation → Deployment | 已存在，继续大幅扩写 |
| `JOB_SKILLS.md` | 招聘样本、技能频率、项目映射、缺口与优先级 | 已建立第一版 |
| `INTERVIEW_ALGORITHMS.md` | Hot100 + 高频补充 + SQL + Backend/AI Coding + System Design | 已建立第一版 |
| `ENGINEERING_REFERENCE.md` | 架构、关键模块、配置、运行时与故障排查 | 待由旧文档合并 |
| `EVALUATION.md` | 检索/生成/Agent 评测、实验设计、指标和结果边界 | 待由旧评测文档合并 |
| `ROADMAP.md` | 已实现 / 部分实现 / 未实现，按招聘价值与工程价值排序 | 待建立 |

## 旧文档迁移原则

当前目录仍有 `architecture.md`、`code_walkthrough.md`、`context-engineering.md`、`design.md`、`evaluation-lab.md`、`evaluation.md`、`experiment-notes-2026-09.md`、`hiring-alignment-2026-09.md`、`interview.md`、`learning-path.md`、`resume-guide.md`、`security.md`、`technology-radar-2026.md`、`tuning.md` 等文件。

这些文件**现在先不删**。下一阶段按下面规则处理：

- 学习原理、示例、跟做、代码阅读：迁入主教材。
- 招聘 JD、技能覆盖、岗位差距：迁入 `JOB_SKILLS.md`。
- 算法、笔试、面试 Coding：迁入 `INTERVIEW_ALGORITHMS.md`。
- 架构、安全、运行时、配置、排错：合并为工程参考。
- 评测方法、实验数据、消融与失败分析：合并为评测参考。
- 未来计划：只进入 Roadmap，不和“已实现”混写。
- 只有确认内容已经迁移、链接已修复后，才删除旧文件。

## 教材统一写法

主教材以后每个重要知识点尽量遵循同一个顺序：

**为什么需要 → 直觉 → 原理 → 最小例子 → 项目真实代码 → 输入输出 → 跟着运行 → 预期结果 → 修改实验 → 常见错误 → trade-off → 招聘为什么问 → 面试怎么解释。**

几个硬规则：

- 先教，再练，再复习；不允许没讲就考。
- 第一次出现的缩写和术语必须解释。
- 公式先讲用途，再用小数字例子，最后才给公式。
- 每项能力区分：讲解 / Demo / 已实现 / 有测试 / 有效果证据 / 未实现。
- “代码存在”不等于“已经掌握”，更不等于“生产级验证”。
- 不因为 JD 出现一个词就强行接一个框架。

## 项目真实代码地图

当前项目已经有足够多的真实工程代码，教材必须绑定这些文件，而不是写成通用教程：

- `src/rag_agent/ingest/loaders.py`：文件解析。
- `src/rag_agent/ingest/chunker.py`：分块。
- `src/rag_agent/ingest/indexer.py`：幂等索引与双库存储协调。
- `src/rag_agent/retrieval/vector_store.py`：Dense / Qdrant。
- `src/rag_agent/retrieval/sqlite_store.py`：SQLite / FTS5。
- `src/rag_agent/retrieval/fusion.py`：RRF。
- `src/rag_agent/retrieval/hybrid.py`：Hybrid Retrieval。
- `src/rag_agent/retrieval/reranker.py`：CrossEncoder 重排。
- `src/rag_agent/agent/graph.py`：LangGraph、查询规划、证据门控、上下文、生成、引用与有界重试。
- `src/rag_agent/agent/guardrails.py`：安全边界。
- `src/rag_agent/llm/client.py`：模型 API 适配。
- `src/rag_agent/api/main.py`：FastAPI / REST / SSE。
- `src/rag_agent/mcp/server.py`：只读 MCP。
- `src/rag_agent/evaluation/`：离线评测与指标。
- `tests/`：各模块可验证行为。

## 后续整理验收标准

整理完成后，一个第一次打开仓库的人应该能快速回答：

1. 项目解决什么问题？
2. 新电脑怎么启动？
3. 一份文件怎样一路变成带引用的回答？
4. Dense、Sparse、RRF、rerank 分别解决什么？
5. 为什么需要证据门控、拒答和引用校验？
6. 当前 Agent 到底“Agent”在哪里，哪些高级能力还没有？
7. 代码在哪里修改？修改后怎么验证？
8. 企业 Agent Backend 还要求什么？
9. 算法与 Coding 面试该怎么练？
10. 下一阶段最值得升级什么？

只要上述问题仍需要在十几份 Markdown 中来回找答案，文档重构就还没有完成。
