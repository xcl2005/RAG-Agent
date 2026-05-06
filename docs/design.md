# 系统设计说明

## 1. 背景

真实企业资料往往很多，包括制度文档、项目文档、接口文档、会议纪要、论文、FAQ 等。大模型无法一次性读取全部资料，因此需要 RAG：先检索相关资料，再让大模型基于资料回答。

## 2. 为什么需要混合检索

向量检索擅长语义相似，但不一定擅长精确匹配。例如：

- 错误码 `ERR_4039`
- 表名 `user_order_relation`
- 政策条款编号
- 人名、项目名、缩写

关键词检索擅长精确匹配，但对同义表达较弱。所以本项目使用：

- Qdrant：dense vector retrieval。
- SQLite FTS5：sparse keyword retrieval。
- RRF：融合两路结果。

## 3. 为什么需要 rerank

第一阶段检索通常为了速度，会召回 top 40 或 top 100。这里面可能有噪声。CrossEncoder rerank 会同时读取 query 和 document，比单独 embedding 更精细，但成本更高。因此它只适合放在第二阶段，对少量候选排序。

## 4. Agent 工作流

本项目使用 LangGraph，不是为了炫技，而是为了把 RAG 流程拆成清晰节点：

1. rewrite_query：把用户问题改写为检索 query。
2. retrieve：混合检索 + rerank。
3. grade_evidence：判断证据是否足够。
4. generate_answer：基于上下文生成答案。

这样未来容易加：

- 人工确认。
- 多轮记忆。
- SQL 工具。
- Web 搜索工具。
- 文件上传工具。

## 5. 幻觉控制

RAG 不能完全消灭幻觉，但可以降低风险：

- 检索不到就拒答。
- 只基于上下文回答。
- 强制来源引用。
- 设置较低 temperature。
- 返回 sources 供用户核查。

## 6. 大批量资料时的瓶颈

资料增多后主要瓶颈：

1. embedding 入库速度。
2. 向量库查询延迟。
3. reranker 计算成本。
4. 上下文过长导致 LLM 成本上升。
5. 文档增量更新和权限控制。

优化方向：

- 批量 embedding。
- 增量索引。
- 限制 rerank 候选数量。
- 文档去重。
- 按租户、部门、文件类型过滤。
- 热门 query 缓存。
