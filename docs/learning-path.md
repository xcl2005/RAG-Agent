# 从会写 Python 到讲清这个项目

此页保留作可选复习清单，不再作为初学入口。按你的偏好，**只需先读 [单文档手册](PROJECT_HANDBOOK.md)**，
其中先讲解原理、提供示例与操作，再做练习；不要求还没学就回答本页问题。

你的起点：能写基础 Python，但还讲不清项目。先不要求通读整个仓库，也不把框架名当能力。
目标是能独立追踪一次请求、解释一次失败、完成一个小改动并用测试证明它。

每天建议 45–60 分钟；14 天是练习安排，不是保证熟练的期限。某天讲不清就多练一天。

## 今天只做这三步

打开 PyCharm 的 Terminal，确认当前目录是项目根目录：

```powershell
.\.venv\Scripts\python scripts/practice_interview.py show q01
.\.venv\Scripts\python -m pytest tests/test_agent_graph.py -q
```

1. 先用自己的话说：用户的问题从进入网站到出现答案，中间经历什么？允许看代码，不看参考答案。
2. 只读 `graph.py::_build_graph`，看节点连接，不必读全部 900 多行。
3. 再看解析，比较你漏了哪个环节：

```powershell
.\.venv\Scripts\python scripts/practice_interview.py show q01 --reveal
```

第一句可以从这里开始：“模型没有直接读取全部文件。资料先切块入库，问题进来后检索相关块，
通过门控和上下文预算后才交给模型，最后检查引用编号。”然后追问自己：资料不足时在哪儿停止？

## 怎样使用练习工具

```powershell
.\.venv\Scripts\python scripts/practice_interview.py list
.\.venv\Scripts\python scripts/practice_interview.py show q05
.\.venv\Scripts\python scripts/practice_interview.py show q05 --reveal
.\.venv\Scripts\python scripts/practice_interview.py record q05 --score 1 --note "知道门控作用，还不能解释错误放行"
.\.venv\Scripts\python scripts/practice_interview.py status
```

只有你主动 `record` 才记录本人自评；`show` 不算掌握。默认进度在 `reports/learning-progress.json`，
被 Git 忽略，不上传、不调用 LLM、不自动判定你会不会。分数含义：0 说不出；1 能复述；
2 能指着代码解释；3 能独立修改并验证。示例分数不是建议你照填。

## 14 天安排

每天分配：10 分钟复述昨天 → 15 分钟读指定函数/测试 → 20 分钟动手 → 10 分钟记录和追问。

| 天 | 题目/阅读范围 | 当天交付与验收 |
|---|---|---|
| 1 | q01；`graph.py::_build_graph` | 画出请求流程，指出哪些节点用模型、哪些不需要模型。 |
| 2 | q02；`chunker.py::recursive_split` | 运行 `tests/test_chunker.py`；用纸解释太大/太小/重叠的代价。 |
| 3 | q03；`hybrid.py::retrieve_many_with_debug` | 对比“错误码 401”和“凭证失效”，解释词法与向量各擅长什么。 |
| 4 | q04；`fusion.py` | 手算两个排名列表的 RRF；运行 `tests/test_rrf.py` 对照。 |
| 5 | q05；`graph.py::assess_evidence` | 完成实验 A；同时解释误拒答与错误放行的分母。 |
| 6 | q06；`prompts.py::build_context` | 完成实验 B；能解释转义后长度、分隔符和候选副本。 |
| 7 | q06；`graph.py::prepare_context` | 完成实验 C；说明为何不同章节不能只按正文去重。 |
| 8 | q07；`guardrails.py::validate_citations` | 构造合法 `[S1]` 但语义不被支持的答案，说明校验盲区。 |
| 9 | q08；`llm/client.py` 的输出检查 | 完成实验 D；区分模型失败、证据不足和引用失败。 |
| 10 | q09；`initialize` / `finalize` | 解释 `thread_id`、最近 6 轮、持久化与进程内任务的区别。 |
| 11 | q10；`indexer.py::ingest_file` | 用“Qdrant 成功、SQLite 失败”解释权威回表，不声称分布式原子事务。 |
| 12 | q11；`api/main.py` / `mcp/server.py` | 区分模型 Key 与本地访问 Key，说明 MCP 只读和公网部署的欠缺。 |
| 13 | q12；`evaluation/lab.py` | 完成实验 E；保存数据标签、哈希、两类错误和下一步计划。 |
| 14 | [模拟面试](interview.md) | 进行一次 20 分钟录音演练；不看稿讲 90 秒项目、展示测试和失败案例。 |

每天另留 10 分钟补基础：HTTP 状态码与 SSE；list/dict/set 和复杂度；异常处理和单元测试；
事务、索引、进程/线程。这些仍是招聘基础，本项目不能代替算法题与计算机基础复习。

## 五个需要你亲手完成的实验

这些任务没有被标记为已完成。建议把自己的记录保存在 `reports/my-experiments.md`：
“原先猜测 → 只改了什么 → 结果 → 失败点 → 取舍”。

### A. 门控阈值是不是越低越好？

```powershell
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.45
.\.venv\Scripts\python scripts/eval_portfolio.py --sparse-threshold 0.25
```

验收：两次排序结果应一致，门控决定可能变化。分别计算误拒答/可回答题数、错误放行/不可回答题数。
挑 `p04` 和 `n08` 解释，不只抄总指标。追问：为什么主题相关仍然不一定能回答？

### B. 文本被截断，quote 为什么不能用完整原文？

只在测试里构造长 Candidate，把“最终结论”放到末尾。给 `build_context` 320 字符预算，
检查返回 quote 是否包含模型看不到的末尾。参考 `tests/test_prompts.py` 的构造方式，亲手写一个新测试。

验收：原 Candidate 不被修改；`character_count == len(text) <= 320`；quote 不含被裁掉的内容。
追问：字符预算为什么不等于 token 预算？如果关键答案在末尾，你会怎样选择句窗？先写方案，不盲增预算。

### C. 相同句子为什么可能不能去重？

构造同一文档两个 Candidate，正文相同，一个 `heading=Production`，另一个 `heading=Staging`。
运行去重，再改成同一 heading；观察候选数量。增加自己的 page 范围或数字冲突测试。

验收：不同范围/数字/否定保留，同范围真重复才合并；用 30 秒解释为什么。
追问：大量相似申请文书该用什么更细的评测，才能决定是否引入语义去重？

### D. API 返回成功码但模型正文为空怎么办？

复制 `tests/test_agent_graph.py` 的 FakeLLM 写一个返回空白正文的用例，不调用真实 GLM。
运行 `tests/test_llm_client.py` 和 `tests/test_agent_graph.py`。

验收：结果不是成功答案；`failure_kind` 是 `generation_failure`，不是 `insufficient_evidence`；
已过门控的资料仍可用于排查。追问：如果开启 reasoning 导致输出预算耗尽，首先检查哪些字段？

### E. 自己制作 5 道未用于调规则的题

把 `data/eval/portfolio` 复制到自己的实验目录。先写 5 题，至少一题跨文档、一题词很像却缺答案。
给出相关文件和原文摘录，负例写清缺哪条事实。运行时用 `--dataset-dir` 指向该目录。

验收：数据验证通过，保存新 SHA256；不能为了提升分数删掉失败题。若规则作者见过这些题，
它们只是新增开发题，不是独立测试集；真正保留集应由别人出题并在冻结规则后运行。
追问：8 份资料里 Recall@5=1 为什么仍不能叫“生产效果很好”？

## 你什么时候可以写进简历

至少完成 A + B + E，能不看稿解释两个失败案例，并现场改一个测试。
这只是本项目的建议验收，不是招聘通过保证。用 [简历指南](resume-guide.md) 区分已有功能、
AI 辅助代码和你亲自完成的改动；如果不会某一层，就明确它还在学习中。
