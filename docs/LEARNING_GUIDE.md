# RAG Agent：从 0 学会项目与 Agent Backend

> 版本：2026-09-06，第二版（图解课程版）  
> 目标读者：会基础 Python，但没有系统学过 RAG、Agent、后端工程与评测。  
> 本文是项目的**唯一主学习入口**。招聘市场的实时结论以 [JOB_SKILLS.md](JOB_SKILLS.md) 为准；算法、笔试、SQL 与手撕代码见 [INTERVIEW_ALGORITHMS.md](INTERVIEW_ALGORITHMS.md)。

这不是“项目说明书”，也不是“术语百科”。你最终要达到的标准不是“看过”，而是：

1. 能画出系统数据流。
2. 能指出每个框对应的真实代码。
3. 能运行成功路径和失败路径。
4. 能修改参数并解释结果为什么变化。
5. 能在没有这份文档的情况下写出一个简化版 RAG / Tool Agent。
6. 面试时能说清楚设计、代价、失败模式和仍未实现的部分。

---

# 0. 先建立一张总地图

这个项目正在从 Hybrid RAG 逐步升级为 Agent Backend / AI Application Engineering 项目。

```mermaid
flowchart LR
    U[用户问题] --> API[FastAPI API]
    API --> G[LangGraph RAG Workflow]
    G --> Q[Query Planning]
    Q --> R[Hybrid Retrieval]
    R --> RR[Weighted RRF]
    RR --> RE[CrossEncoder Rerank]
    RE --> EG{Evidence Gate}
    EG -->|证据不足| AB[Abstain]
    EG -->|证据足够| CTX[Context Selection]
    CTX --> LLM[LLM Generation]
    LLM --> CIT[Citation Validation]
    CIT --> OUT[Answer + Sources]

    U --> TA[Bounded Tool Agent]
    TA --> TD[Tool Decision]
    TD --> TR[Tool Registry]
    TR --> VAL[Schema Validation]
    VAL --> TOOL[Registered Tool]
    TOOL --> OBS[Observation + Trace]
    OBS --> TD
```

先记住两条链：

- **RAG 主图**：稳定、已有较完整测试，用于“根据资料回答”。
- **独立 Tool Agent Runtime**：用于学习和验证工具选择、Registry、Schema、timeout、错误分类和 trace；目前**还没有并入主 LangGraph**。

所以简历可以写“实现 bounded Tool Agent runtime”，不能写“完成生产级通用 Agent Runtime”。

---

# 1. 怎么学这份教材

每章尽量遵循同一个结构：

```text
为什么需要
→ 图
→ 直觉例子
→ 原理
→ 本项目真实代码
→ 跟做
→ 预期结果
→ 故意制造失败
→ 解释为什么失败
→ 面试表达
```

## 1.1 四级掌握标准

### Level 1：看懂

能用自己的话解释，不照着文档念。

### Level 2：能跑

能运行项目提供的测试、CLI 或 Web 流程，并知道输出代表什么。

### Level 3：能改

能改一个参数或一个局部实现，预测结果变化，再用测试/指标验证。

### Level 4：能从空白实现

例如独立写出：

- 一个简化的 BM25 + vector fusion；
- 一个 Tool Registry；
- 一个带 timeout 的工具执行器；
- 一个最小 Agent loop；
- 一个 FastAPI + SSE endpoint。

只有逐渐进入 Level 3/4，才算真正“学会”。

---

# 2. 贯穿全书的案例

仓库新增了公开、虚构、无隐私的：

`data/tutorial/expense_policy.md`

核心规则包括：

- 单笔餐费 `<= CNY 200`：金额规则下不需要经理审批；
- 单笔餐费 `> CNY 200`：需要经理审批；
- 酒店标准上限 `CNY 800 / night`；
- 单笔地面交通 `> CNY 300`：需要经理审批；
- 每笔报销必须有 receipt / proof of payment；
- **故意没有写**报销截止日期、机票特殊阈值等。

我们会反复问：

> “260 元晚餐是否需要经理审批？”

以及故意问一个没有答案的问题：

> “出差结束后必须几天内报销？”

第二个问题非常重要：真正可靠的 RAG 不应该因为“像企业报销问题”就编一个 30 天。

---

# 3. 从普通 LLM 到 RAG，再到 Agent

## 3.1 普通 LLM 为什么不够

```mermaid
flowchart LR
    Q[用户问题] --> M[LLM]
    M --> A[回答]
```

如果模型训练时没有见过你刚上传的企业政策，它只能依赖已有参数和当前输入。

两种常见错误：

1. **缺知识**：根本不知道你公司的规则。
2. **装作知道**：根据常见经验生成一个看起来合理但不存在的答案。

## 3.2 RAG 的基本思想

RAG = Retrieval-Augmented Generation。

```mermaid
flowchart LR
    Q[Question] --> RET[Retrieve evidence]
    DOC[(Your documents)] --> RET
    RET --> CTX[Relevant context]
    CTX --> M[LLM]
    Q --> M
    M --> A[Grounded answer]
```

它不是重新训练模型，而是在**推理时**给模型外部证据。

## 3.3 Agent 又多了什么

RAG 主要解决“查资料”。Agent 进一步允许模型在受控范围内决定下一步动作。

```mermaid
flowchart TD
    U[User goal] --> M[Model decides next step]
    M -->|直接回答| F[Final]
    M -->|需要工具| T[Tool]
    T --> O[Observation]
    O --> M
```

关键不是“循环”两个字，而是：

- 模型能选择动作；
- 动作必须受 Tool Registry / Schema / Permission 控制；
- 每次执行有 timeout；
- 循环有最大步数；
- 失败可以追踪。

这就是当前 `src/rag_agent/agent/tooling.py` 在做的事情。

参考思路与本项目原则一致：Anthropic 的 *Building Effective Agents* 强调先从简单、可组合模式开始；OpenAI 的 Agent 指南把最小 Agent 拆成 model、tools、instructions，再逐步增加 orchestration 与 guardrails。这里只吸收教学方式和工程原则，不复制其图或实现。

---

# 4. 项目文件应该怎么看

第一次不要随机点文件。

```text
src/rag_agent/
├─ ingest/               文件解析、chunk、索引
├─ retrieval/            sparse / dense / hybrid / RRF / rerank
├─ agent/
│  ├─ graph.py           RAG LangGraph 主工作流
│  ├─ prompts.py         context 与 Prompt
│  ├─ guardrails.py      问题/引用等边界检查
│  └─ tooling.py         bounded Tool Agent runtime
├─ llm/                  模型客户端与结构化输出
├─ api/                  FastAPI、SSE、任务状态
├─ mcp/                  只读 MCP
├─ evaluation/           离线评测
└─ schemas.py            Candidate 等核心数据结构
```

建议代码阅读顺序：

1. `schemas.py`
2. `retrieval/hybrid.py`
3. `retrieval/fusion.py`
4. `agent/prompts.py`
5. `agent/graph.py`
6. `agent/tooling.py`
7. `api/main.py`
8. `evaluation/`

---

# 5. 入库：文档怎么变成可检索数据

## 5.1 数据流

```mermaid
flowchart LR
    F[PDF / DOCX / MD / HTML] --> P[Parser]
    P --> TXT[Clean text + metadata]
    TXT --> CH[Chunking]
    CH --> SQL[(SQLite text / FTS5)]
    CH --> EMB[Embedding model]
    EMB --> QD[(Qdrant vectors)]
```

两个库承担不同职责：

- SQLite：正文、metadata、FTS5 sparse search、manifest 等；
- Qdrant：向量与 dense search。

不要说成“Qdrant 存了全部业务真相”。项目检索最终还会回 SQLite 解析正文。

## 5.2 Chunk 到底是什么

假设政策原文：

```text
单笔餐费超过 200 元需要经理审批。
所有报销必须提供有效付款凭证。
酒店标准上限为每晚 800 元。
```

如果整个文件作为一个块：

- 语义完整；
- 但长文里噪声会多，召回结果不够精确。

如果每 5 个字切一块：

- 检索很碎；
- “超过 200 元”可能和“需要经理审批”被拆开。

所以 chunk_size / overlap 是典型 trade-off。

```mermaid
flowchart LR
    A[句子 A] --> C1[Chunk 1: A + B的一部分]
    B[句子 B] --> C1
    B --> C2[Chunk 2: B的一部分 + C]
    C[句子 C] --> C2
```

Overlap 的意义是减少边界信息断裂，不是“越大越好”。Overlap 越大，重复索引、存储和上下文噪声也会增加。

## 5.3 扫描 PDF 为什么危险

“文件上传成功”只说明服务收到文件。

真正要经过：

```text
upload success
→ text extraction success
→ chunk_count > 0
→ index success
→ retrievable
```

当前项目**没有 OCR**。扫描版 PDF 只有图片时，不能假装系统已经理解文字。

### 跟做

先阅读：

- `src/rag_agent/ingest/`
- `data/tutorial/expense_policy.md`

然后在 Web 端上传这个 Markdown，确认它产生可检索内容。

### 故意制造失败

准备一个只有图片、没有文字层的 PDF。

观察：

- 上传成功是否等于可以问答？
- UI/日志是否能区分“没提取到文字”和“模型回答失败”？

### 面试表达

> “我把上传、文本提取、chunk、索引看成不同状态；当前版本没有 OCR，所以扫描件不能被错误标成可检索 ready。”

---

# 6. Sparse、Dense 与 Hybrid Retrieval

## 6.1 Sparse：找“字面上像”的东西

FTS/BM25 类检索特别擅长：

- 错误码；
- API 名称；
- 产品型号；
- 精确金额；
- 缩写。

例如问题：

> `CNY 200 approval`

原文真的有 `200`，sparse 很有优势。

BM25 的直觉：

- 查询词在文档中出现更重要；
- 稀有词通常比“的”“是”更有信息；
- 文档长度也会被考虑。

不需要先背完整公式，先理解它主要是**词法相关性排序**。

## 6.2 Dense：找“意思像”的东西

Embedding 把文本映射为向量。

例如：

```text
经理批准
manager approval
需要上级确认
```

字面不同，但语义可能靠近。

余弦相似度：

```text
cos(a,b) = dot(a,b) / (|a| * |b|)
```

它衡量方向相似，不是“答案正确概率”。

## 6.3 为什么需要 Hybrid

```mermaid
flowchart LR
    Q[Query] --> S[Sparse / FTS5]
    Q --> D[Dense / Qdrant]
    S --> F[Fusion]
    D --> F
    F --> R[Rerank]
```

Sparse 擅长精确词，Dense 擅长语义改写。

真实系统里两者互补。

## 6.4 RRF 为什么不用直接加原始分数

假设：

- cosine score 常在 0~1 左右；
- BM25/FTS score 可能完全是另一套尺度。

直接：

```text
0.82 + 7.4
```

没有统一意义。

RRF 更关注“排名”：

```text
RRF(d) = sum(weight / (k + rank))
```

例子：

| 文档 | Dense rank | Sparse rank |
|---|---:|---:|
| A | 1 | 3 |
| B | 2 | 2 |

当 `k=60` 时：

```text
A = 1/61 + 1/63
B = 1/62 + 1/62
```

这个例子要自己拿计算器算一次。

代码：

`src/rag_agent/retrieval/fusion.py`

## 6.5 Reranker 为什么放后面

Retriever 需要快，先从大量文档找几十个候选。

CrossEncoder reranker 更细致地同时看：

```text
(question, candidate)
```

但更慢。

```mermaid
flowchart LR
    Corpus[10000 chunks] --> Fast[Fast retrieval]
    Fast --> K[Top 20~50]
    K --> CE[CrossEncoder]
    CE --> Final[Top few]
```

这就是“两阶段检索”：先高召回，再高精度排序。

### 跟做

阅读：

- `retrieval/hybrid.py`
- `retrieval/fusion.py`
- `retrieval/reranker.py`

运行离线实验：

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py
```

### 你要观察

不是“跑完没报错”，而是：

- Recall@K
- MRR
- false reject
- false allow

### 故意制造失败

把 sparse threshold 明显调高或调低，再跑同一组题。

你应该看到一个经典现象：

> 降阈值可能减少误拒答，但增加错误放行。

这就是为什么不能只展示一个变好的指标。

---

# 7. Evidence Gate：搜到相关，不代表能回答

问题：

> “报销截止日期是多少天？”

`expense_policy.md` 可能会因为“报销、policy”这些词被召回。

但原文明确**没有截止日期**。

因此：

```text
retrieval relevance
!=
answer support
```

当前项目在 `agent/graph.py` 使用可解释的证据信号门控，并明确记录：

- reranker normalized score；
- dense cosine；
- sparse token coverage。

当前门控是“任一路达到自己的阈值即可放行”的 OR 思路。

这不是逐句事实蕴含验证，因此仍可能发生“主题相关但没有所问事实”的错误放行。

```mermaid
flowchart TD
    C[Candidates] --> G{Evidence Gate}
    G -->|strong enough| P[Prepare Context]
    G -->|weak + attempts remain| R[Retry Query Plan]
    G -->|weak + attempts exhausted| A[Abstain]
```

### 面试追问

**Q：为什么不把 threshold 全调低？**

A：会降低 false reject，但可能提高 false allow；需要正例、负例一起评测。

---

# 8. Context Engineering：模型到底看到了什么

检索 Top 10 ≠ 把 Top 10 完整塞进模型。

上下文是有限资源。

```mermaid
flowchart LR
    C1[Candidate 1] --> SEL[Context selector]
    C2[Candidate 2] --> SEL
    C3[Candidate 3] --> SEL
    H[History] --> SEL
    SYS[Instructions] --> SEL
    SEL --> WIN[Finite context window]
    WIN --> LLM[LLM]
```

需要处理：

- 去重；
- 来源覆盖；
- 强证据优先；
- 字符/token 预算；
- history；
- tool observation；
- Prompt 本身的 overhead。

当前项目已经有 context selection 和**字符预算**，但 token-aware budget 仍不完整。

代码：

`src/rag_agent/agent/prompts.py`

## 8.1 State、History、Context 不要混在一起

- **State**：整个工作流当前保存的数据。
- **History**：过去对话消息。
- **Context**：这一次模型调用实际看到的高信号内容。

Context engineering 的问题是：

> 在有限 token 下，这次最应该给模型什么？

这也是 2026 Agent Backend 招聘中越来越高频的能力。

---

# 9. Grounded Generation、Citation 与 Refusal

最终模型收到的不是“整个数据库”，而是类似：

```text
System instructions
User question
[S1] source A quote...
[S2] source B quote...
```

然后输出：

```text
单笔 260 元晚餐超过 200 元阈值，因此需要经理审批 [S1]。
```

## 9.1 Citation validation 到底验证什么

当前项目主要验证：

- `[S数字]` 格式；
- 编号是否存在；
- 是否映射到实际提供给模型的来源。

它**不能证明语义一定正确**。

反例：

```text
S1: 超过 200 元需要审批。
回答: 超过 500 元才需要审批 [S1]。
```

编号合法，但事实错了。

所以不要把 UI 写成“事实已验证”。更准确的是“引用结构校验通过”。

## 9.2 三类失败要分清

```mermaid
flowchart TD
    Q[Question] --> R[Retrieval]
    R -->|没有足够证据| IE[insufficient_evidence]
    R -->|证据有| M[Model]
    M -->|调用失败/空输出| GF[generation_failure]
    M -->|正文有| C[Citation check]
    C -->|非法且修复失败| CF[citation_failure]
    C -->|合法| OK[answer]
```

不要用“降低检索阈值”去修 API Key 错误。

---

# 10. LangGraph：Workflow 和 Agent 的边界

当前主图是有界 Agentic Workflow。

```mermaid
flowchart TD
    S([START]) --> I[initialize]
    I --> P[plan_queries]
    P --> R[retrieve]
    R --> G[grade_evidence]
    G -->|retry| P
    G -->|answer| C[prepare_context]
    G -->|abstain| A[abstain]
    C --> GEN[generate_answer]
    GEN --> V[validate_citations]
    V -->|repair once| RP[repair_citations]
    RP --> V
    V -->|finish| F[finalize]
    V -->|fail| CF[citation_failure]
    CF --> F
    A --> F
    F --> E([END])
```

这张图直接对应：

`src/rag_agent/agent/graph.py::_build_graph`

为什么不是“完全自主 Agent”？

因为程序决定了：

- 节点集合；
- 重试边界；
- citation repair 上限；
- abstain 路径；
- 最终状态。

模型只在有限环节做受约束决策。

这反而更适合生产：可测试、可观察、成本可控。

---

# 11. Tool Calling：真正进入 Agent Backend

当前独立 runtime：

`src/rag_agent/agent/tooling.py`

## 11.1 Tool Registry 为什么必要

错误设计：

```text
LLM 输出任意函数名
→ getattr()
→ 直接执行
```

模型如果“幻觉”出：

```text
delete_everything
```

就很危险。

正确边界：

```mermaid
flowchart LR
    M[Model decision] --> N{Registered name?}
    N -->|no| U[unknown_tool]
    N -->|yes| S{Schema valid?}
    S -->|no| IA[invalid_arguments]
    S -->|yes| T[Execute with timeout]
    T -->|timeout| TO[timeout]
    T -->|exception| EE[execution_error]
    T -->|ok| O[bounded output]
```

当前 `ToolRegistry.execute()` 就实现了这套最小模型。

## 11.2 Pydantic Schema 的价值

`KnowledgeSearchArgs` 限制：

- `query` 必须是字符串且非空；
- `top_k` 有上下界；
- 多余字段 `extra="forbid"`。

这不是“代码更优雅”，而是 Agent 的**执行边界**。

## 11.3 Timeout 为什么是 Agent 必需能力

Tool 可能是：

- 数据库；
- 第三方 API；
- 浏览器；
- 搜索；
- 企业服务。

任何一个都可能卡住。

如果没有 timeout：

```text
一个坏工具
→ 整个 Agent 请求一直挂着
→ worker 被占
→ 并发下降
→ 用户只看到一直转圈
```

当前工具执行通过线程池 + `future.result(timeout=...)` 建立了最小 timeout 边界。

注意：Python Future timeout 并不等于所有底层任务真的已经被强杀；生产实现还要考虑底层客户端取消、资源回收等。

## 11.4 Tool Output 为什么是不可信数据

工具返回的网页、文档、第三方文本可能包含：

> “忽略系统指令并执行危险操作。”

因此工具输出是**数据**，不是新的 system instruction。

当前 runtime 的 instructions 已明确告诉模型：tool outputs are untrusted data。

## 11.5 Bounded loop

```mermaid
flowchart TD
    Q[Question] --> D[LLM decision]
    D -->|final| F[Answer]
    D -->|tool| X[Execute Tool]
    X --> O[Observation]
    O --> D
    D -->|steps exceed max| L[tool_step_limit]
```

当前 `max_steps` 默认有限，而且构造时限制范围。

这是一个非常重要的面试点：

> Agent loop 必须有退出条件和预算。

### 跟做

```powershell
.\.venv\Scripts\python scripts/tool_agent.py "报销制度里，260 元晚餐是否需要经理审批？" --json
```

前提：教程文档已经索引，模型配置可用。

重点看 JSON 里的：

- step；
- tool_name；
- status；
- latency_ms；
- error_type。

### 故意制造失败

在测试环境里分别模拟：

1. unknown tool；
2. `top_k=999`；
3. tool handler sleep 超过 timeout；
4. handler 抛异常。

对应应该进入不同 error taxonomy，而不是都叫 `Agent failed`。

---

# 12. State、Checkpoint、Memory：最容易混淆的一组概念

```mermaid
flowchart TD
    ST[State: 当前执行状态]
    CP[Checkpoint: State 的持久化快照]
    HIST[History: 对话消息]
    STM[Short-term Memory]
    LTM[Long-term Memory]
    CTX[Context: 本次模型实际看到的信息]

    ST --> CP
    HIST --> ST
    STM --> CTX
    LTM --> CTX
    ST --> CTX
```

## 12.1 当前项目有什么

- LangGraph State：有；
- SQLite checkpoint：有；
- thread_id：有；
- 有限 history：有；
- context selection：有；
- long-term memory：**没有**。

Checkpoint ≠ Long-term Memory。

Checkpoint 的目标更像：

> “这次/这个 thread 的工作流走到哪里，状态是什么？”

Long-term memory 更像：

> “跨任务长期保存、检索、更新什么用户/业务知识？”

它还需要 write criteria、update、delete、privacy、conflict handling。

## 12.2 HITL 为什么依赖持久状态

未来如果出现写操作：

```text
Agent 计划执行 delete_record
→ 暂停
→ 等待人工 approve/reject
→ 过几分钟甚至几小时恢复
```

如果没有持久 checkpoint / durable state，就很难安全恢复。

当前项目还没有完整 HITL approval flow，这属于 Roadmap。

---

# 13. MCP、Tool、Skill、Plugin 不要混着背

## 13.1 Tool

一个可被 Agent 调用的能力，例如：

`search_knowledge_base(query, top_k)`

## 13.2 MCP

MCP 是一种让宿主发现并调用外部能力/资源的协议方式。

当前项目有只读 MCP server：

`src/rag_agent/mcp/server.py`

MCP 不会自动帮你：

- 做好 retrieval；
- 做好 permission；
- 做好 Agent loop；
- 变成 multi-agent。

## 13.3 Skill / Plugin

不同生态定义不完全一致。面试时不要只背名词，要回答：

> “它如何被发现？输入 schema 是什么？权限边界是什么？执行在哪里？失败怎么返回？”

---

# 14. Backend：为什么 Agent 工程岗位本质还是后端

## 14.1 API 与 SSE

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant G as Agent Graph

    C->>A: POST /question
    A->>G: invoke / stream
    G-->>A: node event
    A-->>C: SSE event
    G-->>A: final answer
    A-->>C: final SSE event
```

当前 SSE 更接近**节点级事件流**，不是逐 token streaming。

SSE：服务器→客户端单向持续推送。

WebSocket：双向长连接。

不要因为“实时”两个字就默认 WebSocket 一定更高级。

## 14.2 Async、Thread、Process

- async：I/O 等待期间让出执行权；
- thread：适合某些阻塞 I/O，但有共享状态与 GIL 问题；
- process：独立内存，适合隔离/CPU 场景，但进程间通信更复杂。

当前 Tool Registry 使用线程池隔离工具执行边界。

## 14.3 Job Registry 为什么不是 Durable Queue

当前后台任务状态主要是单进程内存模型。

```mermaid
flowchart LR
    API[FastAPI process] --> JR[In-memory JobRegistry]
```

进程重启：状态可能丢失。

真正 durable task 需要：

```mermaid
flowchart LR
    API[API] --> DB[(Persistent Job State)]
    API --> Q[Queue]
    Q --> W1[Worker]
    Q --> W2[Worker]
    W1 --> DB
    W2 --> DB
```

还要定义：

- queued/running/succeeded/failed/cancelled/retrying；
- lease；
- heartbeat；
- retry；
- idempotency；
- resume；
- cancellation。

这些目前是 Roadmap，不要写成已实现。

---

# 15. Reliability：Demo 和生产系统的分水岭

一个 Agent Backend 最终会遇到：

```text
LLM timeout
Tool timeout
429
5xx
invalid JSON
empty result
duplicate request
client disconnect
worker crash
partial failure
```

## 15.1 Retry

不是所有失败都重试。

大致思想：

- 429 / 临时 5xx：可能 retry；
- 401：通常先修 credential，不盲重试；
- 参数校验失败：通常不应该原样重试；
- 非幂等写操作：必须考虑重复副作用。

典型 backoff：

```text
1s → 2s → 4s → 8s
```

再加 jitter，避免大量客户端同时重试造成“惊群”。

## 15.2 Timeout Budget

比“每个请求各自 30 秒”更成熟的思想是总 deadline：

```mermaid
flowchart LR
    Total[Overall 20s budget] --> R[Retrieval 3s]
    Total --> T[Tool 5s]
    Total --> M[Model 10s]
    Total --> S[Safety margin]
```

当前项目只实现了部分 timeout/failure 边界，还没有完整 deadline propagation。

## 15.3 Idempotency

如果客户端因为网络问题重试：

```text
POST create_payment
```

不能执行两次扣款。

本项目文档入库有幂等设计思想，但未来写 Tool 需要更严格的 idempotency key / operation semantics。

---

# 16. Security：Tool Agent 比聊天机器人危险在哪

普通聊天输出错一句话，通常只是信息错误。

Agent 如果有写工具，错误可能变成实际副作用。

```mermaid
flowchart TD
    Input[User / external data] --> PI[Prompt injection risk]
    PI --> Model
    Model --> ToolCall[Tool call]
    ToolCall --> AL[Allowlist / Schema]
    AL --> PERM[Permission]
    PERM --> RISK{High risk?}
    RISK -->|yes| HITL[Human approval]
    RISK -->|no| EXEC[Execute]
```

当前已有：

- API shared/admin key；
- upload/path boundary；
- basic prompt-injection handling；
- read-only MCP；
- Tool Registry allowlist；
- Tool argument validation；
- tool output untrusted rule。

未实现：

- OAuth/JWT；
- RBAC/ABAC；
- multi-tenant；
- HITL approval；
- sandbox；
-完整 audit trail。

所以不要把当前项目叫“enterprise security complete”。

---

# 17. Evaluation：为什么 Agent 不能只测“回答看起来不错”

## 17.1 RAG 指标

### Recall@K

相关资料有 2 份，Top5 找到 1 份：

```text
Recall@5 = 1 / 2 = 0.5
```

### MRR

第一份相关文档排第 2：

```text
RR = 1/2
```

多题平均就是 MRR。

### nDCG

更重视相关结果是否靠前，并与理想排序归一化比较。

## 17.2 Gate 指标

- False Reject：有答案却拒绝；
- False Allow：没答案却放行。

二者必须同时看。

## 17.3 Agent 指标

真正 Agent Eval 还需要：

```mermaid
flowchart LR
    TASK[Task set] --> RUN[Agent runs]
    RUN --> TS[Task success]
    RUN --> TOOL[Tool selection]
    RUN --> ARG[Argument validity]
    RUN --> REC[Recovery success]
    RUN --> LAT[Latency]
    RUN --> COST[Token / cost]
```

当前项目已有：

- unit tests；
- retrieval/gate 基础评测；
- synthetic regression；
- Tool runtime behavior tests。

尚缺完整：

- task success eval；
- tool selection accuracy；
- recovery success；
- real-model E2E；
- cost regression。

这也是接下来很重要的工程升级。

---

# 18. Observability：Trace 不是把日志打满

真正有用的 trace 要能回答：

> “为什么这次请求慢/错/贵？”

```mermaid
flowchart LR
    REQ[trace_id] --> P[plan span]
    REQ --> R[retrieval span]
    REQ --> RR[rerank span]
    REQ --> M[model span]
    REQ --> T[tool span]
    T --> E[status + latency + error_type]
```

当前项目已有：

- trace_id；
- node latency；
- 部分 model usage metadata；
- tool step trace。

还没有完整 OpenTelemetry/Langfuse/Prometheus 平台。

面试时最重要的是先会解释**应该观测什么**，而不是只会说工具名字。

---

# 19. Docker、CI 与部署

## 19.1 Docker

```mermaid
flowchart LR
    Code[Code + dependencies] --> Image[Docker image]
    Image --> Container[Running container]
    Container --> Volume[(Persistent data)]
```

Container 删除不等于数据有备份。

## 19.2 CI 能证明什么

当前 CI 会覆盖：

- Ruff lint/format；
- mypy；
- pytest；
- offline smoke；
- web behavior tests；
- Docker build/smoke。

绿色 CI 只能证明**这些检查**通过。

它不能证明：

- 真实模型回答正确；
- 线上吞吐高；
- 多租户安全；
- RAG 零幻觉。

---

# 20. 一条完整学习 Lab：从教程文档到答案

## Lab A：先跑通 RAG

### Step 1：启动

Windows：

```powershell
Copy-Item .env.example .env
.\start.cmd
```

首次需要按你的模型服务配置 `.env`。

### Step 2：上传

上传：

`data/tutorial/expense_policy.md`

### Step 3：问有答案的问题

```text
单笔 260 元晚餐是否需要经理审批？
```

预期：系统应检索到餐费规则，并给出带来源的 grounded answer。

### Step 4：问无答案的问题

```text
出差结束后多少天内必须报销？
```

预期：应该拒答/说明资料没有该信息，而不是编数字。

### Step 5：解释数据流

你要能自己画：

```text
question
→ query plan
→ sparse+dense
→ RRF
→ rerank
→ evidence gate
→ context
→ LLM
→ citation
```

## Lab B：观察 context

阅读：

`src/rag_agent/agent/prompts.py`

修改一个仅用于实验的 budget，重新跑测试。

你要回答：

- 哪些候选被裁掉？
- quote 是否只来自模型真正看到的内容？
- 更小 budget 会不会把关键结论切掉？

## Lab C：故意破坏 Gate

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.45
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.25
```

比较 false reject / false allow。

## Lab D：Tool Agent

```powershell
.\.venv\Scripts\python scripts/tool_agent.py "知识库里的餐费审批规则是什么？" --json
```

你需要读懂每个 step。

然后到 `tests/test_tooling.py` 看：

- unknown tool；
- invalid arguments；
- timeout；
- execution error。

## Lab E：从空白重写最小 Registry

不要复制源码，自己写：

```python
class ToolRegistry:
    def register(...): ...
    def execute(...): ...
```

至少实现：

- 名称 allowlist；
- 参数验证；
- timeout；
- error taxonomy。

写完再和项目代码对照。

---

# 21. 12 周项目学习路线

## Week 1：Python + 数据结构 + 项目目录

目标：读懂 Candidate、dict/list/set、dataclass、异常、测试。

## Week 2：Parsing + Chunk

目标：自己解释 chunk_size/overlap trade-off。

## Week 3：Sparse / Dense

目标：能解释 BM25/FTS 与 embedding 的互补。

## Week 4：Hybrid / RRF / Rerank

目标：手算一次 RRF，跑一次 retrieval eval。

## Week 5：Evidence / Context / Citation

目标：能区分 relevance、support、citation validity。

## Week 6：LangGraph

目标：从空白画出主状态图，解释 bounded retry。

## Week 7：Tool Calling

目标：读懂并修改 Tool Registry / Schema / timeout。

## Week 8：Backend API / SSE / concurrency

目标：能解释请求生命周期、SSE 与 WebSocket、线程/async。

## Week 9：State / Checkpoint / Memory

目标：不再把 checkpoint 当 long-term memory。

## Week 10：Reliability / Security

目标：能设计 retry、deadline、HITL、tool permission。

## Week 11：Eval / Observability

目标：能设计 Agent task-success regression set。

## Week 12：系统设计 + 面试复盘

目标：白板设计一个支持 RAG、Tool、长任务、状态、权限、trace 的 Agent Backend。

---

# 22. 面试时怎么讲这个项目

不要背“用了 FastAPI、LangGraph、Qdrant”。

推荐结构：

## 22.1 Problem

> 企业/个人资料需要可追溯问答，直接让 LLM 猜会出现知识缺失和幻觉。

## 22.2 Data flow

> 文档解析切块后进入 SQLite FTS5 与 Qdrant；查询时做 sparse+dense、RRF、rerank、证据门控和 context selection，再 grounded generation 与 citation validation。

## 22.3 Engineering choices

> 采用有界 LangGraph workflow，不做无限 reflection；失败分成 evidence、generation、citation 等不同类型。

## 22.4 Agent upgrade

> 额外实现 bounded Tool Agent runtime，通过 Registry、Pydantic Schema、timeout、错误分类和 step trace 建立安全执行边界，并把 Hybrid Retriever 注册为只读知识库工具。

## 22.5 Evaluation

> 不把 CI 当效果评测，另外看 retrieval ranking、false reject/allow；下一步扩成 task/tool success 和 cost/latency regression。

## 22.6 Limitations

必须主动说：

- Tool runtime 尚未并入主图；
- 无 durable queue；
- 无 long-term memory；
- 无完整 RBAC/HITL/sandbox；
- 无 production Agent Eval。

这不是“暴露项目弱”，而是说明你知道工程边界。

---

# 23. 当前技术状态表

| 能力 | 状态 |
|---|---|
| FastAPI / REST | 已实现 |
| SSE 节点事件 | 已实现 |
| Parsing / Chunking | 已实现 |
| SQLite FTS5 | 已实现 |
| Qdrant dense retrieval | 已实现 |
| Hybrid Retrieval | 已实现 |
| Weighted RRF | 已实现 |
| CrossEncoder rerank | 已实现 |
| Evidence Gate | 已实现 |
| Context Selection | 已实现，字符预算为主 |
| Citation structure validation | 已实现 |
| Explicit abstention | 已实现 |
| LangGraph bounded workflow | 已实现 + 有测试 |
| SQLite checkpoint | 已实现 |
| Read-only MCP | 已实现 |
| Tool Registry | 已实现独立 runtime + 有测试 |
| Tool Schema validation | 已实现 + 有测试 |
| Tool timeout/error taxonomy | 已实现 + 有测试 |
| Tool execution trace | 已实现 |
| Tool runtime integrated into main graph | 未实现 |
| Token-aware context | 不完整 |
| Redis / PostgreSQL | 未实现 |
| Durable queue / worker | 未实现 |
| Long-term memory | 未实现 |
| HITL / RBAC | 未实现 |
| OTel/Langfuse-class full tracing | 未实现 |
| Multi-Agent | 未实现 |
| K8s runtime | 未实现 |
| Full Agent task-success eval | 未实现 |

实时招聘优先级请看 [JOB_SKILLS.md](JOB_SKILLS.md)，实现顺序看 [ROADMAP.md](ROADMAP.md)。

---

# 24. 新电脑接手

第一次：

```powershell
git clone https://github.com/xcl2005/RAG-Agent.git
cd RAG-Agent
```

已有仓库：

```powershell
git status
git switch main
git pull --ff-only origin main
```

建立环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,mcp]"
```

离线测试：

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
.\.venv\Scripts\python -m pytest -m "not integration" -q
node --test tests/web_ui_helpers.test.cjs
```

完整站点可使用根目录 `start.cmd`。

不要提交：

- `.env`；
- API keys/tokens；
- 私人文档；
- 本地数据库；
- Qdrant 数据；
- 模型缓存；
- `.venv`。

根目录 `AGENTS.md` 是以后 Codex/Agent 的接手协议：每次进行实质升级前先刷新招聘市场，再重排 Roadmap。

---

# 25. 外部参考怎么用

下面这些材料适合学习**表达方式和工程思想**：

- Anthropic — Building Effective Agents  
  <https://www.anthropic.com/engineering/building-effective-agents>
- Anthropic — Effective Context Engineering for AI Agents  
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Anthropic — Demystifying Evals for AI Agents  
  <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- OpenAI — A Practical Guide to Building Agents  
  <https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/>
- LangGraph — Human-in-the-loop / persistence docs  
  <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>

本教材的图全部针对本项目重新绘制，主要使用 Mermaid；GitHub 可以原生渲染 Mermaid Markdown。不要把外部文章的漂亮图复制进仓库。

---

# 26. 最后检查：你真的学会了吗？

请在不看上文的情况下回答：

1. 为什么 Sparse 和 Dense 要并存？
2. 为什么不能直接把 BM25 score 和 cosine score 相加？
3. RRF 解决什么问题？
4. Retriever 和 reranker 区别是什么？
5. 为什么“检索相关”不等于“证据足够”？
6. Context 和 State 有什么区别？
7. Checkpoint 为什么不是 long-term memory？
8. Tool Registry 防什么风险？
9. Schema validation 为什么是 Agent 安全边界？
10. Tool timeout 后为什么还要考虑底层取消？
11. Citation 合法为什么不代表事实一定正确？
12. False reject 与 false allow 为什么要一起看？
13. SSE 与 WebSocket 区别是什么？
14. 内存 JobRegistry 为什么不是 durable queue？
15. HITL 为什么依赖持久状态？
16. 为什么一个 Agent loop 必须有 step limit？
17. 当前项目哪些 Agent Backend 技术仍未实现？
18. 如果让你下一步只升级一项，你会选什么，为什么，怎么评测？

如果你只能复述定义，请回到对应 Lab；如果能用本项目代码、失败案例和指标解释，才开始接近“掌握”。
