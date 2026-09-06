# RAG Agent：从 0 学会这个项目与 Agent Backend

> 版本：2026-09-07，第三版（教学重构版）  
> 适合读者：会基础 Python，但没有系统学过 RAG、Agent、后端工程、评测和可靠性。  
> 目标：读完不是“认识这些词”，而是能跑、能改、能解释、能自己写一个简化版。

这份文档是项目的主学习入口。

招聘市场和技能优先级看 `JOB_SKILLS.md`；算法、SQL、Backend 手撕和 AI Coding 看 `INTERVIEW_ALGORITHMS.md`；后续实现顺序看 `ROADMAP.md`。

---

# 0. 先别看架构：先看这个项目到底解决什么问题

假设公司有一份报销制度：

- 单笔餐费不超过 200 元时，金额规则本身不要求经理审批；
- 单笔餐费超过 200 元时，需要经理审批；
- 酒店标准上限为每晚 800 元；
- 单笔地面交通超过 300 元时，需要经理审批；
- 每一笔报销都必须有付款凭证；
- 文档里**没有写**“出差结束后多少天内必须报销”。

仓库里已经准备了这份教学资料：

`data/tutorial/expense_policy.md`

现在问两个问题。

### 问题 A

> 260 元的晚餐需要经理审批吗？

正确做法应该是：找到“超过 200 元需要审批”的原文，再根据原文回答“需要”。

### 问题 B

> 出差结束后必须几天内报销？

正确做法不是猜“30 天”，而应该说：

> 当前资料没有提供这个期限。

这两个问题就是整个项目的核心。

项目不是为了让模型“说得像真的”，而是为了让它：

1. 找到相关资料；
2. 判断资料够不够回答；
3. 只把真正有用的资料交给模型；
4. 让回答能回到来源；
5. 没证据时明确拒答；
6. 需要行动时，再通过受控 Tool 执行。

如果这六件事你真正理解了，后面的 BM25、Embedding、RRF、LangGraph、Tool Calling 就不会再是一堆孤立名词。

---

# 1. 你最终要学会什么

读这份教材时，不要以“我看完了”为目标。

每一章都按四级掌握。

| 级别 | 你应该做到什么 |
|---|---|
| Level 1：看懂 | 能用自己的话解释，不照着文档念 |
| Level 2：能跑 | 能运行真实项目路径，知道输入和输出 |
| Level 3：能改 | 改一个参数，能预测结果变化并验证 |
| Level 4：能独立实现 | 关掉教材，从空白写一个简化版本 |

最终至少要能独立写出：

- 一个最小文本切块器；
- 一个简单 BM25/关键词检索；
- 一个向量检索调用；
- 一个 RRF 融合函数；
- 一个受限 Tool Registry；
- 一个带 timeout 的 Tool executor；
- 一个最小 Agent loop；
- 一个 FastAPI + SSE 接口。

---

# 2. 先认识项目目录，不要随机点文件

第一次打开仓库时，只记住下面这些入口。

| 目录 / 文件 | 它解决的问题 |
|---|---|
| `src/rag_agent/ingest/` | 文档怎么读出来、切块、建立索引 |
| `src/rag_agent/retrieval/` | 用户问一句话后，怎么找候选证据 |
| `src/rag_agent/agent/graph.py` | RAG 主流程怎么一步步执行 |
| `src/rag_agent/agent/prompts.py` | 真正送给模型的上下文和提示词怎么组织 |
| `src/rag_agent/agent/tooling.py` | Tool 注册、参数校验、timeout、错误分类 |
| `src/rag_agent/api/main.py` | FastAPI 接口和 SSE 输出 |
| `src/rag_agent/api/jobs.py` | 当前后台任务状态怎么保存 |
| `src/rag_agent/mcp/server.py` | 当前只读 MCP 能力 |
| `src/rag_agent/evaluation/` | 怎么判断检索/门控有没有变好 |
| `src/rag_agent/schemas.py` | Candidate 等核心数据结构 |

建议阅读顺序：

1. `schemas.py`
2. `retrieval/hybrid.py`
3. `retrieval/fusion.py`
4. `retrieval/reranker.py`
5. `agent/prompts.py`
6. `agent/graph.py`
7. `agent/tooling.py`
8. `api/main.py`
9. `evaluation/`

为什么不是先看 `main.py`？

因为先从 Web/API 入口读，很容易看到大量路由、配置、异常处理，却不知道真正的 RAG 逻辑在哪里。

---

# 3. 第一件事：文档怎么从一个文件变成可检索数据

这一章先不讲模型。

你只需要理解：**一份长文档不能直接高质量地拿去检索。**

## 3.1 为什么不能整份文件直接搜索

假设文件有 50 页，而用户只问：

> 餐费超过多少钱要审批？

如果整份文件是一个检索单元：

- 用户真正需要的只有一两句话；
- 其余 49 页都是噪声；
- Embedding 会把大量主题混在一起；
- 最终上下文也会非常浪费。

所以要切成 chunk。

## 3.2 Chunk 到底是什么

先看一小段原文：

> 单笔餐费超过 200 元需要经理审批。所有报销必须提供付款凭证。酒店标准上限为每晚 800 元。

如果切得很大，可能得到：

| Chunk | 内容 |
|---|---|
| 1 | 三句话全部放在一起 |

优点：上下文完整。

缺点：当文件变长以后，一个 chunk 里会混进很多无关信息。

如果切得太小，可能变成：

| Chunk | 内容 |
|---|---|
| 1 | 单笔餐费超过 200 元 |
| 2 | 需要经理审批 |
| 3 | 所有报销必须提供付款凭证 |

这又会产生另一个问题：最重要的一条规则被拆成了两半。

因此 `chunk_size` 不是越小越好，也不是越大越好。

## 3.3 overlap 是干什么的

假设一句关键话刚好落在 chunk 边界。

没有 overlap：

- Chunk 1 只留下前半句；
- Chunk 2 只留下后半句。

有适量 overlap：

- Chunk 1 结尾保留一部分；
- Chunk 2 开头重复一部分；
- 关键信息不容易被边界切断。

但 overlap 越大：

- 重复索引越多；
- 存储变大；
- 召回结果更容易出现很多近似重复块；
- 最终 context 也可能变吵。

这就是一个典型 trade-off。

## 3.4 入库真正经历哪些状态

上传成功，只能说明服务器收到文件。

它不等于文件已经可以问答。

你应该把下面这些状态分开理解：

| 状态 | 代表什么 |
|---|---|
| 上传成功 | 文件到达服务端 |
| 文本提取成功 | 能从文件中拿到可用文字 |
| chunk 数大于 0 | 至少产生了一个可检索文本块 |
| 索引成功 | sparse / dense 索引建立完成 |
| 可检索 | 查询真的能找到这些 chunk |

当前项目没有 OCR。

所以纯扫描图片 PDF 即使上传成功，也不能假装“已经读懂”。

### 你现在应该做

打开：

`src/rag_agent/ingest/`

然后观察：

1. 文件怎么被解析；
2. chunk 是在哪里形成的；
3. metadata 是怎么跟着 chunk 保存的；
4. 索引什么时候被认为完成。

### 故意制造失败

准备一个没有文字层的扫描 PDF。

你要观察系统能否区分：

- 文件上传失败；
- 文本提取为空；
- 建索引失败；
- 模型调用失败。

如果四种错误最后全变成一句“系统错误”，这个后端就很难调试。

---

# 4. 为什么项目同时有 Sparse 和 Dense 检索

这是 RAG 最重要的一章之一。

先不要背 BM25 和 Embedding 的定义，先看两个问题。

## 4.1 问题一：精确词

用户问：

> CNY 200 approval

文档里真的出现了 `200`。

这类查询里，数字、错误码、产品型号、函数名、API 名称非常重要。

关键词检索通常很有优势。

## 4.2 问题二：意思相同但字不同

用户问：

> 哪些餐饮支出需要上级确认？

原文却写：

> 单笔餐费超过 200 元需要经理审批。

“上级确认”和“经理审批”字面不同，但意思接近。

这时候 Dense / Embedding 更有优势。

## 4.3 Sparse 是什么

当前项目的 sparse 路径主要依赖 SQLite FTS5 一类词法检索能力。

你先把它理解成：

> 它关心查询词和文档词在字面上的匹配程度。

它通常擅长：

- 精确关键词；
- 数字；
- 专有名词；
- 错误码；
- API / 类名 / 函数名。

BM25 的核心直觉也不复杂：

- 查询词出现很重要；
- 稀有词通常比常见词更有区分度；
- 文档长度需要校正。

现在不需要死背公式。

## 4.4 Dense 是什么

Dense 检索先把一段文本变成向量。

你可以把向量暂时理解成：

> 模型给这段话做出的“语义坐标”。

例如下面三句话字面不同：

- 经理批准；
- manager approval；
- 需要上级确认。

Embedding 可能把它们放得比较近。

项目使用 Qdrant 管理向量检索部分。

注意：向量相似度不是“回答正确率”。

即使某个 chunk 的 cosine similarity 很高，也只能说明它语义上比较像问题，不代表它一定包含回答问题所需的事实。

---

# 5. Hybrid Retrieval：为什么两个检索结果要合起来

假设同一个问题分别得到两个结果。

Sparse：

| 排名 | Chunk |
|---:|---|
| 1 | A |
| 2 | B |
| 3 | C |

Dense：

| 排名 | Chunk |
|---:|---|
| 1 | B |
| 2 | D |
| 3 | A |

你会发现：

- A 在两边都不错；
- B 在两边都很强；
- C 只有 sparse 喜欢；
- D 只有 dense 喜欢。

这就是为什么需要 fusion。

## 5.1 为什么不能直接把原始分数相加

假设：

- Dense 分数是 `0.82`；
- Sparse 分数是 `7.4`。

直接算：

`0.82 + 7.4`

这个数字没有统一意义，因为两个系统的分数尺度不是一回事。

## 5.2 RRF 在做什么

RRF 的核心思想不是比较原始分数，而是比较**排名**。

假设：

| Chunk | Dense 排名 | Sparse 排名 |
|---|---:|---:|
| A | 1 | 3 |
| B | 2 | 2 |

B 在两条检索链上都稳定靠前；A 在 Dense 最强，但 Sparse 稍弱。

RRF 会把“多条检索链都认可”的候选提升。

代码位置：

`src/rag_agent/retrieval/fusion.py`

### 你真正要理解的不是公式

你要能回答：

> 为什么融合排名比直接融合原始分数更稳？

答案是：不同检索器的分数不在同一尺度，而排名天然更容易比较。

---

# 6. Reranker：为什么检索完还要再排一次

假设知识库里有 10000 个 chunk。

如果让一个很重的模型逐个比较：

> 这个问题和这个 chunk 到底相关不相关？

成本会太高。

所以常见做法是两阶段：

### 第一阶段：快速召回

用 sparse + dense 快速找出几十个候选。

### 第二阶段：精细重排

只让 CrossEncoder 一类 reranker 对这几十个候选做更细的比较。

可以理解成：

| 阶段 | 目标 | 重点 |
|---|---|---|
| Retriever | 不要漏掉可能有用的资料 | Recall |
| Reranker | 把真正最相关的排前面 | Precision / Ranking |

当前代码：

- `retrieval/hybrid.py`
- `retrieval/fusion.py`
- `retrieval/reranker.py`

### 跟做

运行：

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py
```

不要只看“程序跑完了”。

至少看：

- Recall@K；
- MRR；
- false reject；
- false allow。

---

# 7. 为什么“搜到了相关资料”仍然可能不能回答

现在回到第二个教学问题：

> 出差结束后必须多少天内报销？

知识库里明明有很多“报销”相关 chunk。

Sparse 和 Dense 很可能都能找到它们。

但是这些 chunk 只是在主题上相关，并没有真正写“多少天”。

所以必须区分两个概念：

| 概念 | 问题 |
|---|---|
| relevance | 这个 chunk 和用户问题像不像？ |
| support | 这个 chunk 里有没有足够事实支持答案？ |

这就是 Evidence Gate 存在的原因。

## 7.1 当前项目怎么做

`agent/graph.py` 会使用几类证据信号做门控，例如：

- reranker normalized score；
- dense cosine；
- sparse token coverage。

当前实现是可解释的规则门控，而不是完整逐句事实蕴含模型。

因此它能降低很多明显无证据回答，但仍不等于“事实验证系统”。

## 7.2 为什么 threshold 不是越低越好

把阈值调低：

- 更容易放行；
- 有答案的问题更少被拒绝；
- 但没答案的问题也更容易错误放行。

把阈值调高：

- 更谨慎；
- 但有些本来能回答的问题也会被拒绝。

所以需要同时看：

- False Reject；
- False Allow。

### 实验

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.45
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.25
```

你的任务不是选“更大的数字”，而是解释两组指标发生了什么变化。

---

# 8. Context Engineering：检索到的资料不等于全部塞给模型

假设检索得到 10 个 chunk。

模型上下文不是无限的。

除了这些 chunk，还要放：

- system instruction；
- 用户问题；
- 对话历史；
- Tool observation；
- 输出格式说明。

因此必须选择真正值得进入本次模型调用的内容。

## 8.1 一个具体例子

假设候选有：

| 候选 | 内容 | 是否应该优先进入 Context |
|---|---|---|
| A | 餐费超过 200 元需要审批 | 是 |
| B | 酒店上限 800 元 | 通常不是当前重点 |
| C | 餐费规则的重复表述 | 可能去重 |
| D | 所有报销要有凭证 | 视问题而定 |

如果用户只问 260 元晚餐是否审批，A 是最核心证据。

把 B、C、D 全塞进去，不一定更好。

更多内容意味着：

- token 增加；
- 成本增加；
- 噪声增加；
- 模型可能把注意力放错地方。

当前项目已经有 context selection 和字符预算；完整 token-aware budget 仍然不完整。

代码：

`src/rag_agent/agent/prompts.py`

## 8.2 State、History、Context 不要混

| 名称 | 你应该怎么理解 |
|---|---|
| State | 整个工作流当前保存的数据 |
| History | 过去的对话消息 |
| Context | 这一次调用模型时真正交给模型看的信息 |

Context Engineering 解决的是：

> 在有限预算里，这一次最应该让模型看到什么？

---

# 9. Prompt、Citation 和 Refusal

模型最终拿到的不是整个数据库。

它拿到的更接近：

- 一组 system instructions；
- 用户问题；
- 经过筛选的来源片段；
- 要求引用来源的输出规则。

例如模型可能看到：

`[S1] 单笔餐费超过 200 元需要经理审批。`

然后回答：

> 260 元超过 200 元阈值，因此需要经理审批 [S1]。

## 9.1 Citation validation 能证明什么

当前项目主要检查：

- 引用格式是不是 `[S数字]`；
- 这个编号是不是存在；
- 是否真的对应模型拿到的来源。

它不能证明整句话语义一定正确。

例如：

来源写的是：

> 超过 200 元需要审批。

模型却回答：

> 超过 500 元才需要审批 [S1]。

引用编号合法，但事实仍然错。

所以更准确的说法是：

> 引用结构校验通过。

而不是：

> 事实已验证。

## 9.2 三种失败必须分开

### 证据不足

没有足够资料支持回答。

### 生成失败

模型 API timeout、空输出、服务异常。

### 引用失败

模型回答出来了，但引用结构不合法，并且修复失败。

这三种问题的修法完全不同。

如果 API Key 错了，降低检索阈值毫无意义。

---

# 10. LangGraph：先理解“程序规定流程”，再学框架

不要先把 LangGraph 当成一个神秘 Agent 框架。

先看当前 RAG 主流程实际在做什么。

| 顺序 | 步骤 | 它解决什么问题 |
|---:|---|---|
| 1 | initialize | 初始化这次请求状态 |
| 2 | plan_queries | 生成/整理检索查询 |
| 3 | retrieve | 找候选证据 |
| 4 | grade_evidence | 判断证据是否足够 |
| 5 | prepare_context | 选择模型真正看到的资料 |
| 6 | generate_answer | 生成回答 |
| 7 | validate_citations | 检查引用结构 |
| 8 | finalize | 整理最终结果 |

如果证据不足，还可能：

- 重新规划查询；
- 达到重试上限后拒答。

如果引用不合法，还可能：

- 做一次受限 repair；
- 再失败就进入 citation failure。

代码：

`src/rag_agent/agent/graph.py`

## 10.1 为什么这不是“无限自主 Agent”

因为程序已经规定：

- 有哪些节点；
- 哪些地方能重试；
- 最多重试多少次；
- 什么时候必须退出；
- 什么时候拒答。

这反而是工程优势。

它更容易：

- 测试；
- 观察；
- 限制成本；
- 复现失败。

---

# 11. Tool Calling：Agent 为什么比 RAG 更危险

RAG 主要是在“查资料”。

Tool Calling 开始允许模型触发一个真实能力。

例如：

- 搜知识库；
- 查数据库；
- 调企业 API；
- 发消息；
- 创建任务。

一旦 Tool 有写操作，模型错误就可能产生真实副作用。

所以不能让模型随便输出一个函数名就直接执行。

## 11.1 Tool Registry

当前项目有独立 runtime：

`src/rag_agent/agent/tooling.py`

Registry 的核心作用是：

> 只有明确注册过的 Tool 才能执行。

假设模型输出：

`delete_everything`

如果这个名字没注册，系统应该返回：

`unknown_tool`

而不是使用 `getattr()` 随便找函数。

## 11.2 参数 Schema

假设知识库 Tool 定义：

- `query`：必须是非空字符串；
- `top_k`：必须在合理范围；
- 不允许额外字段。

那么模型传：

`top_k = 999`

系统应该在执行之前拒绝。

这就是 Pydantic Schema 的工程价值：

> 它不是为了“代码优雅”，而是执行边界。

## 11.3 Timeout

Tool 可能会卡住。

例如第三方 API 10 分钟不返回。

如果没有 timeout：

- 这次 Agent 请求一直占着 worker；
- 并发下降；
- 用户只看到一直等待；
- 下游资源也可能积压。

当前 Tool executor 已经有最小 timeout 边界。

但是要注意：

Python Future timeout 并不自动等于底层所有网络请求都真正被强制终止。

生产实现还需要考虑：

- 客户端取消；
- socket/request deadline；
- 资源回收。

## 11.4 错误分类

当前 runtime 会区分至少这些情况：

| 错误 | 代表什么 |
|---|---|
| `unknown_tool` | Tool 名称不在 Registry |
| `invalid_arguments` | 参数 Schema 不通过 |
| `timeout` | 超过执行时间 |
| `execution_error` | Tool 内部抛异常 |

这比统一返回：

`Agent failed`

有价值很多。

因为你终于知道下一步该修哪里。

## 11.5 最大步数

Agent loop 必须有预算。

如果模型不断：

- 调 Tool；
- 看结果；
- 再调 Tool；
- 永远不结束；

就会造成成本和延迟失控。

当前 bounded runtime 有 `max_steps`。

### 跟做

```powershell
.\.venv\Scripts\python scripts/tool_agent.py "报销制度里，260 元晚餐是否需要经理审批？" --json
```

重点不要只看最终答案。

看每一步：

- step；
- tool_name；
- status；
- latency_ms；
- error_type。

### 故意制造失败

在测试里观察：

- unknown tool；
- 非法 `top_k`；
- timeout；
- handler exception。

对应测试：

`tests/test_tooling.py`

---

# 12. State、Checkpoint、History、Memory 到底有什么区别

这是 Agent 学习里最容易混的一组词。

## 12.1 State

State 是：

> 这次工作流当前保存的全部执行数据。

可能包括：

- 用户问题；
- 当前候选文档；
- 重试次数；
- 当前回答；
- 引用检查结果。

## 12.2 Checkpoint

Checkpoint 是：

> 把某个时刻的 State 保存下来。

目的通常是：

- 恢复；
- 调试；
- 暂停继续；
- 失败后重启。

当前项目有 SQLite checkpoint。

## 12.3 History

History 只是过去对话消息。

它属于 State 的一种可能数据，但不等于完整 State。

## 12.4 Long-term Memory

Long-term Memory 是另一回事。

例如系统长期记住：

- 用户偏好；
- 企业常用对象；
- 跨任务形成的稳定知识。

它还需要：

- 什么值得写入；
- 怎么更新；
- 怎么删除；
- 冲突怎么办；
- 隐私怎么办。

当前项目没有完整 long-term memory。

## 12.5 为什么 HITL 依赖持久状态

假设未来 Agent 要执行高风险操作：

> 删除一条记录。

正确流程可能是：

1. Agent 计划删除；
2. 系统暂停；
3. 等用户审批；
4. 10 分钟以后用户点击同意；
5. 系统从刚才的状态恢复；
6. 再执行 Tool。

如果所有状态只放在进程内存里，服务一重启就丢了。

所以 durable state 和 HITL 往往联系很紧。

---

# 13. MCP、Tool、Skill 不要靠背名词区分

## Tool

一个 Agent 可以调用的具体能力。

例如：

`search_knowledge_base(query, top_k)`

## MCP

可以先理解为：

> 一套让宿主发现和调用外部工具/资源的协议方式。

当前项目有只读 MCP server：

`src/rag_agent/mcp/server.py`

但“用了 MCP”不代表：

- 自动有安全权限；
- 自动有好用的 Agent loop；
- 自动有高质量 RAG；
- 自动变成 multi-agent。

## Skill / Plugin

不同平台定义可能不同。

面试时比名词更重要的是回答：

1. 它怎么被发现？
2. 输入 Schema 是什么？
3. 谁允许执行？
4. 在哪里执行？
5. timeout 怎么办？
6. 失败怎么返回？

---

# 14. 为什么 Agent Backend 仍然首先是 Backend

Agent 最终还是运行在一个真实服务里。

用户不会只问：

> 你的 prompt 写得好吗？

还会问：

- API 怎么设计？
- 并发怎么办？
- 用户断开连接怎么办？
- 状态放哪里？
- 服务重启怎么办？
- Tool timeout 怎么办？
- 重复请求怎么办？
- 如何鉴权？
- 如何追踪一次失败？

这就是为什么现在 Agent Backend 招聘里经常同时出现 Python/Java/Go、数据库、Redis、MQ、Docker、K8s、Agent、RAG、Eval。

---

# 15. FastAPI 与 SSE

当前 API 入口：

`src/rag_agent/api/main.py`

## 15.1 SSE 是什么

SSE 适合服务器持续向客户端推送事件。

当前项目更接近“节点级事件流”，不是严格逐 token streaming。

你可以把一次请求理解成：

| 时间 | 服务端发生什么 | 前端看到什么 |
|---:|---|---|
| 0s | 请求进入 FastAPI | 开始处理 |
| 0.2s | 完成 retrieval | 一个进度事件 |
| 0.5s | 完成 rerank | 一个进度事件 |
| 1.3s | 模型生成完成 | 最终回答事件 |

SSE 和 WebSocket 不要简单理解成“低级/高级”。

### SSE

- 主要是服务端 → 客户端；
- 简单；
- 很适合状态和流式文本推送。

### WebSocket

- 双向长连接；
- 更适合客户端和服务端都持续主动发消息的场景。

---

# 16. Async、Thread、Process 怎么选

这三个词不要只背定义。

## async

适合大量 I/O 等待。

例如：

- 等模型 API；
- 等数据库；
- 等网络请求。

等待期间可以让出执行权。

## thread

适合某些阻塞 I/O。

但你要考虑：

- 共享状态；
- 锁；
- Python GIL；
- 线程泄露。

当前 Tool executor 使用线程池建立最小隔离和 timeout 边界。

## process

独立内存，更适合：

- CPU 密集；
- 强隔离；
- 某些不可信任务。

但进程间通信更复杂。

---

# 17. 当前 Job Registry 为什么还不算 Durable Task

当前：

`src/rag_agent/api/jobs.py`

它是一个小型进程内任务状态模型。

这对 portfolio / 单进程 demo 很实用。

但进程重启后，内存状态可能消失。

真正 durable task 通常至少需要：

| 能力 | 为什么需要 |
|---|---|
| 持久化 job state | 服务重启后状态还在 |
| Queue | API 和真正执行任务解耦 |
| Worker | 独立消费任务 |
| Retry | 临时失败可以恢复 |
| Idempotency | 防止重复执行副作用 |
| Lease / heartbeat | 判断 worker 是否还活着 |
| Cancellation | 用户能取消长任务 |
| Resume | 中断后从合适位置继续 |

这些目前还属于 Roadmap。

不要在简历里写“已经有生产级 durable execution”。

---

# 18. Reliability：为什么 Demo 一上线就容易暴露问题

真实系统会遇到：

- LLM timeout；
- Tool timeout；
- 429；
- 5xx；
- invalid JSON；
- empty result；
- duplicate request；
- client disconnect；
- worker crash；
- partial failure。

## 18.1 Retry 不是失败就重试

### 可能重试

- 临时 429；
- 某些临时 5xx；
- 短暂网络错误。

### 通常不应该原样重试

- 401 credential 错误；
- 参数 Schema 错误；
- 明确业务拒绝。

### 写操作更危险

如果 Tool 是：

`create_payment`

客户端超时以后重试一次，可能造成两次付款。

所以重试必须和 idempotency 一起讨论。

## 18.2 Exponential Backoff

常见等待可以逐渐增加：

- 第一次等待 1 秒；
- 第二次 2 秒；
- 第三次 4 秒；
- 第四次 8 秒。

真实系统一般还会加 jitter，避免很多客户端同一时刻一起重试。

## 18.3 Deadline 比单个 timeout 更完整

假设用户整个请求只允许 20 秒。

你不能让：

- retrieval 最多 20 秒；
- tool 再最多 20 秒；
- model 再最多 20 秒。

否则总请求可能变成 60 秒。

更成熟的设计是维护整体 deadline，再把剩余预算分给后续步骤。

当前项目还没有完整 deadline propagation。

---

# 19. Security：Agent 的错误为什么可能产生真实后果

普通聊天机器人说错一句话，通常只是信息错误。

如果 Agent 有 Tool：

- 删除文件；
- 发邮件；
- 改数据库；
- 创建订单；

错误就可能产生真实副作用。

所以生产 Agent 至少要考虑：

| 防线 | 作用 |
|---|---|
| Tool allowlist | 不允许模型随便执行函数 |
| Schema validation | 阻止非法参数 |
| Authentication | 谁在调用系统 |
| Authorization | 这个用户能不能做这件事 |
| HITL | 高风险操作先人工确认 |
| Sandbox | 不可信代码/浏览器任务隔离 |
| Audit | 以后能查谁做了什么 |
| Prompt injection defense | 外部数据不能变成最高权限指令 |

当前项目已有部分：

- API shared/admin key；
- upload/path boundary；
- 基础 prompt-injection handling；
- read-only MCP；
- Tool allowlist；
- 参数 validation；
- tool output 作为 untrusted data。

当前还没有完整：

- OAuth/JWT；
- RBAC/ABAC；
- multi-tenant ACL；
- HITL approval；
- sandbox；
- 完整 audit trail。

---

# 20. Evaluation：怎么知道系统真的变好了

“我问了几个问题，看起来不错”不是评测。

## 20.1 Recall@K

假设某问题真正相关的资料有 2 份。

Top5 只找到 1 份。

那么：

`Recall@5 = 1 / 2 = 0.5`

它关注：

> 该找的资料有没有找回来。

## 20.2 MRR

如果第一份相关资料排第 2：

`RR = 1 / 2`

多个问题平均就是 MRR。

它关注：

> 第一份有用结果出现得够不够靠前。

## 20.3 Gate 指标

### False Reject

资料其实能回答，系统却拒绝。

### False Allow

资料其实不能回答，系统却放行模型回答。

这两个必须一起看。

## 20.4 Agent Eval

真正 Agent 还应该评：

- Task Success；
- Tool Selection Accuracy；
- Argument Validity；
- Tool Success；
- Recovery Success；
- Latency；
- Token / Cost。

当前项目已有：

- unit tests；
- retrieval/gate 基础评测；
- synthetic regression；
- Tool runtime behavior tests。

仍然缺完整：

- task success eval；
- tool selection accuracy；
- recovery success；
- real-model E2E；
- cost regression。

---

# 21. Observability：日志多不等于看得懂系统

真正有价值的问题是：

> 为什么这次请求慢？

> 为什么这次请求错？

> 为什么这次请求特别贵？

所以一次请求至少希望能看到：

| 阶段 | 值得记录什么 |
|---|---|
| Query Planning | 花了多久、生成了什么查询 |
| Retrieval | 命中多少、每路结果如何 |
| Rerank | 候选如何变化 |
| Model | latency、token、error |
| Tool | tool_name、status、latency、error_type |
| Final | 最终状态、是否拒答 |

当前已经有：

- trace_id；
- node latency；
- 部分 model usage metadata；
- tool step trace。

还没有完整 OpenTelemetry / Langfuse / Prometheus 生产链路。

面试时先说明“要观测什么”，再说具体平台。

---

# 22. Docker 和 CI 到底证明什么

当前 CI 会检查：

- Ruff lint / format；
- mypy；
- pytest；
- offline smoke；
- Web behavior tests；
- Docker build / smoke。

绿色 CI 只能证明：

> 这些自动检查通过。

它不能证明：

- 真实模型回答一定正确；
- RAG 没有幻觉；
- 线上能扛高并发；
- 多租户绝对安全。

这也是为什么“代码测试”和“AI 效果评测”必须分开。

---

# 23. 一条完整 Lab：真正把整个项目跑一遍

这一章不要只读。

## Lab 1：启动项目

Windows：

```powershell
Copy-Item .env.example .env
.\start.cmd
```

按照你使用的模型服务填写 `.env`。

## Lab 2：上传教学文件

上传：

`data/tutorial/expense_policy.md`

确认：

- 文本能解析；
- chunk 数大于 0；
- 索引成功。

## Lab 3：问一个有答案的问题

> 单笔 260 元晚餐是否需要经理审批？

你要确认：

1. 检索到了餐费规则；
2. 关键证据进入 context；
3. 回答有来源；
4. 最终结论与来源一致。

## Lab 4：问一个没答案的问题

> 出差结束后多少天内必须报销？

你要确认：

- 系统没有凭经验编一个数字；
- 最终进入拒答/证据不足路径。

## Lab 5：观察检索指标

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py
```

记录：

- Recall@K；
- MRR；
- false reject；
- false allow。

## Lab 6：故意改阈值

分别跑高阈值和低阈值。

在纸上先写预测：

- false reject 会怎么变？
- false allow 会怎么变？

然后再运行。

## Lab 7：Tool Agent

```powershell
.\.venv\Scripts\python scripts/tool_agent.py "知识库里的餐费审批规则是什么？" --json
```

不要只看 final answer。

逐项看：

- 哪一步调用 Tool；
- Tool 名称；
- 参数；
- latency；
- status；
- error_type。

## Lab 8：故意打坏 Tool

阅读：

`tests/test_tooling.py`

找到：

- unknown tool；
- invalid args；
- timeout；
- execution error。

然后自己解释为什么四种失败不能合并成一个异常。

## Lab 9：从空白写最小 Registry

不要复制项目源码。

你自己写一个最小版本，要求至少有：

- register；
- name allowlist；
- argument validation；
- timeout；
- structured error。

写完以后再和 `tooling.py` 对照。

---

# 24. 12 周学习顺序

| 周 | 学什么 | 你必须做到什么 |
|---:|---|---|
| 1 | Python + 项目目录 | 能读 Candidate、dict/list/set、异常、测试 |
| 2 | Parsing + Chunk | 能解释 chunk_size/overlap trade-off |
| 3 | Sparse + Dense | 能解释关键词检索和语义检索各自优势 |
| 4 | Hybrid + RRF + Rerank | 能手算一次 RRF，跑一次 eval |
| 5 | Evidence + Context + Citation | 能区分 relevance、support、citation validity |
| 6 | LangGraph | 能不用图，按顺序讲完整主流程 |
| 7 | Tool Calling | 能从空白写最小 Registry + timeout |
| 8 | FastAPI + SSE + concurrency | 能解释一次请求生命周期 |
| 9 | State + Checkpoint + Memory | 不再把 checkpoint 当 long-term memory |
| 10 | Reliability + Security | 能设计 retry、deadline、idempotency、HITL |
| 11 | Eval + Observability | 能设计 task/tool success regression set |
| 12 | System Design + 模拟面试 | 能设计一个完整 Agent Backend |

---

# 25. 面试时怎么讲这个项目

不要这样讲：

> 我用了 FastAPI、LangGraph、Qdrant、CrossEncoder、MCP。

这只是报技术名词。

应该按问题讲。

## 25.1 Problem

> 企业资料问答最大的风险不是“模型不够聪明”，而是资料找错、证据不足时模型仍然生成看似合理的答案。

## 25.2 Retrieval

> 我把文档切块后同时建立 SQLite FTS5 sparse index 和 Qdrant dense index；查询时走 hybrid retrieval，再用 weighted RRF 融合，并用 CrossEncoder 做第二阶段重排。

## 25.3 Evidence

> 检索相关不代表足以回答，所以我保留了 evidence gate，并同时评 false reject 和 false allow，而不是只追求少拒答。

## 25.4 Generation

> 真正送给模型的是经过预算和去重的 context，回答要求引用来源；引用检查目前验证的是结构和来源编号，不夸大成事实蕴含验证。

## 25.5 Agent

> 在 RAG 主图之外，我实现了一个 bounded Tool Agent runtime，通过 Registry、Pydantic Schema、timeout、错误分类、step limit 和 trace 建立最小安全执行边界。

## 25.6 Limitations

主动说：

- Tool runtime 还没并入主 LangGraph；
- 没有 durable queue；
- 没有完整 long-term memory；
- 没有 RBAC/HITL/sandbox；
- 没有完整 production Agent Eval。

知道边界不是缺点。

不知道边界才是。

---

# 26. 当前技术状态

| 能力 | 当前状态 |
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
| Context Selection | 已实现，主要是字符预算 |
| Citation structure validation | 已实现 |
| Explicit abstention | 已实现 |
| LangGraph bounded workflow | 已实现 + 有测试 |
| SQLite checkpoint | 已实现 |
| Read-only MCP | 已实现 |
| Tool Registry | 独立 runtime 已实现 + 有测试 |
| Tool Schema validation | 已实现 + 有测试 |
| Tool timeout/error taxonomy | 已实现 + 有测试 |
| Tool execution trace | 已实现 |
| Tool runtime integrated into main graph | 未实现 |
| Token-aware context | 不完整 |
| Redis / PostgreSQL | 未实现 |
| Durable queue / worker | 未实现 |
| Long-term memory | 未实现 |
| HITL / RBAC | 未实现 |
| 完整 OTel/Langfuse tracing | 未实现 |
| Multi-Agent | 未实现 |
| Kubernetes runtime | 未实现 |
| Full Agent task-success eval | 未实现 |

实时招聘要求以 `JOB_SKILLS.md` 为准。

---

# 27. 新电脑怎么继续

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

建立 Python 环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,mcp]"
```

离线检查：

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
.\.venv\Scripts\python -m pytest -m "not integration" -q
node --test tests/web_ui_helpers.test.cjs
```

完整站点可使用：

`start.cmd`

不要提交：

- `.env`；
- API Key / Token；
- 私人文档；
- 本地 SQLite / Qdrant 数据；
- 用户上传内容；
- 模型缓存；
- `.venv`。

根目录 `AGENTS.md` 是 Codex/Agent 接手协议。

---

# 28. 你什么时候算真正学会这个项目

最后闭卷回答下面这些问题。

1. 为什么整份 PDF 不应该直接作为一个检索块？
2. chunk overlap 为什么既有好处又有代价？
3. Sparse 和 Dense 分别擅长什么？
4. 为什么原始 Sparse/Dense score 不能随便直接相加？
5. RRF 为什么适合融合不同检索器？
6. Retriever 和 Reranker 的目标有什么区别？
7. relevance 和 answer support 为什么不是一回事？
8. 为什么降低 evidence threshold 可能增加错误回答？
9. Context 和 History 有什么区别？
10. Citation validation 为什么不能证明事实正确？
11. 当前 LangGraph 为什么叫 bounded workflow？
12. Tool Registry 为什么不能换成任意 `getattr()`？
13. Schema validation 解决什么真实风险？
14. timeout 为什么不是“体验优化”，而是资源边界？
15. State、Checkpoint、Memory 有什么区别？
16. 为什么 durable task 需要持久状态和 worker？
17. retry 为什么必须同时考虑 idempotency？
18. SSE 和 WebSocket 应该怎么选？
19. Agent Eval 为什么不能只看最终回答好不好？
20. 当前项目最重要的 5 个未实现生产能力是什么？

如果你只能背答案，回到对应章节重新做 Lab。

如果你能不看文档解释清楚，并且能从空白写最小版本，才算真正学会。
