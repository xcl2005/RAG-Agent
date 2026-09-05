# Adaptive RAG Agent

一个面向 **Agent Backend / AI Application Engineering** 学习与求职展示的工程项目。

它从企业知识库 RAG 出发，已经包含 Hybrid Retrieval、RRF、reranker、证据门控、引用校验、LangGraph 有界工作流、FastAPI/SSE、MCP、离线评测和基础安全边界；同时有一个独立的 **bounded Tool Agent runtime**，用于学习和验证 Tool Registry、参数 Schema、超时、失败分类与执行 trace。

> 项目目标不是把所有热门框架堆在一起，而是把“能运行、能测试、能解释、能评测”的 AI 应用后端逐步做完整。

## 先看这四份文档

- **从 0 学项目（图解课程）**：[docs/LEARNING_GUIDE.md](docs/LEARNING_GUIDE.md)
- **企业到底招什么**：[docs/JOB_SKILLS.md](docs/JOB_SKILLS.md)
- **算法 / 笔试 / 手撕 / SQL / AI Coding（图解训练）**：[docs/INTERVIEW_ALGORITHMS.md](docs/INTERVIEW_ALGORITHMS.md)
- **下一步怎么升级**：[docs/ROADMAP.md](docs/ROADMAP.md)

主教材使用公开虚构案例 [data/tutorial/expense_policy.md](data/tutorial/expense_policy.md) 贯穿文档入库、Hybrid RAG、LangGraph、Tool Agent、State/Checkpoint/Memory、Reliability、Security 和 Eval。大量流程图直接用 GitHub 原生 Mermaid 渲染，因此图和代码一起版本化。

工程实现和评测细节：

- [工程与架构参考](docs/ENGINEERING_REFERENCE.md)
- [评测与实验](docs/EVALUATION.md)
- [文档总入口](docs/README.md)

## 当前真实能力

### RAG 主链路

```text
文件
→ 解析
→ chunk
→ SQLite FTS5 + Qdrant dense index
→ 多查询检索
→ weighted RRF
→ CrossEncoder rerank
→ evidence gate
→ context selection
→ grounded generation
→ citation validation
→ answer / explicit abstention
```

代码入口：

- `src/rag_agent/ingest/`：解析、切块、幂等索引
- `src/rag_agent/retrieval/hybrid.py`：Dense + Sparse 混合检索
- `src/rag_agent/retrieval/fusion.py`：weighted RRF
- `src/rag_agent/retrieval/reranker.py`：CrossEncoder 重排
- `src/rag_agent/agent/graph.py`：LangGraph 工作流、证据门控、上下文、生成和引用处理
- `src/rag_agent/api/main.py`：FastAPI / SSE / 文档上传
- `src/rag_agent/mcp/server.py`：只读 MCP
- `src/rag_agent/evaluation/`：离线评测

### Tool Agent runtime

代码：

- `src/rag_agent/agent/tooling.py`
- `scripts/tool_agent.py`
- `tests/test_tooling.py`

它提供：

- 显式 Tool Registry
- Pydantic 参数 Schema 校验
- unknown tool / invalid arguments / timeout / execution error 分类
- 工具输出长度边界
- 工具输出作为不可信数据
- 最大 Agent 步数
- 每一步 tool execution trace
- 把当前 Hybrid Retriever 注册为只读 `search_knowledge_base` 工具

运行：

```powershell
.\.venv\Scripts\python scripts/tool_agent.py "知识库里的超时策略是什么？" --json
```

这是一条**独立可运行的教学/工程链路**，还没有替换现有稳定 RAG 主图。因此不能把项目描述成“已经完成通用生产 Agent Runtime”。

## 当前没有实现什么

招聘文档里出现不等于项目已经有。

目前仍明确未完成或不完整的包括：

- Redis / PostgreSQL 生产状态层
- Kafka / RabbitMQ / durable task queue
- 真正可恢复的 long-running task
- 完整 long-term memory
- HITL 审批流
- OAuth/JWT/RBAC/ABAC
- 多租户 ACL
- 完整 sandbox / computer-use isolation
- 多 Agent 协作
- Kubernetes / 大规模 Agent 调度
- 完整 OpenTelemetry / Langfuse 生产追踪
- 完整 Agent task-success / tool-success / cost regression eval
- OCR / 多模态文档 RAG
- 逐句事实蕴含验证

这些都放在 [ROADMAP](docs/ROADMAP.md)，按招聘价值和工程价值排序。

## 为什么这个项目不只叫 RAG Demo

**AI Application**

- RAG
- LLM structured output
- context engineering
- citation / refusal
- MCP
- Tool Agent runtime

**Backend**

- FastAPI
- SSE
- SQLite
- Qdrant
- background ingestion
- Docker
- API authentication boundary
- 文件安全边界
- CI / tests

**Agent Engineering**

- bounded workflow
- state/checkpoint
- tool registry
- tool schema validation
- tool timeout/error taxonomy
- trace
- explicit step limit

**Evaluation**

- unit tests
- retrieval metrics
- gate failure metrics
- isolated synthetic portfolio set
- regression thinking

真正还需要继续补的是“生产 Agent 后端”的 durable execution、权限、任务队列、状态与评测闭环。

## 快速开始

### Windows

```powershell
git clone https://github.com/xcl2005/RAG-Agent.git
cd RAG-Agent
Copy-Item .env.example .env
.\start.cmd
```

如果只想学习离线逻辑，不需要模型 Key：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,mcp]"
.\.venv\Scripts\python scripts/eval_portfolio.py
.\.venv\Scripts\python -m pytest -m "not integration" -q
```

完整 Web 应用默认：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## 配置边界

`.env` 至少按需要配置：

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=
LLM_API_MODE=responses
API_ACCESS_KEY=
ADMIN_API_KEY=
```

不要提交：

- `.env`
- API Key / Token
- 私人 PDF / 成绩单 / 简历
- SQLite / Qdrant 本地数据
- 用户上传内容
- 模型缓存
- `.venv`

## 测试

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
.\.venv\Scripts\python -m pytest -m "not integration" --cov=rag_agent
node --test tests/web_ui_helpers.test.cjs
```

CI 的代码覆盖率门槛不等于 RAG/Agent 效果。

效果必须看：

- Recall@K
- MRR / nDCG
- 误拒答
- 错误放行
- task success
- tool success
- latency
- token / cost
- groundedness / citation support

当前后四类还没有完整生产级评测。

## 求职定位

这个项目更适合往这些岗位发展：

1. Agent Backend / 智能体后端
2. AI Application Engineer / AI 应用研发
3. LLM Application Engineer / 大模型应用研发
4. RAG Engineer
5. AI Full-stack（偏后端）
6. Agent Infra（进阶）

不适合作为“纯大模型训练 / 后训练算法”项目包装。

招聘技能来源、公司样本和项目差距见 [docs/JOB_SKILLS.md](docs/JOB_SKILLS.md)。算法和 Coding 面试路线见 [docs/INTERVIEW_ALGORITHMS.md](docs/INTERVIEW_ALGORITHMS.md)。

## 项目原则

以后每个新技术都经过：

```text
招聘/业务需求
→ 为什么需要
→ 最小可验证实验
→ 实现
→ 自动测试
→ 效果评测
→ 图解/学习文档
→ 面试表达
```

不要反过来：

```text
看到热门词
→ 装一个库
→ README 写“已掌握”
```

根目录 [AGENTS.md](AGENTS.md) 是 Codex/Agent 的接手协议：实质升级前先刷新招聘市场，并保持图解课程和项目真实状态同步。

## License

MIT
