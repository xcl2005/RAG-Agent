# Adaptive RAG Agent 示例资料

## 系统定位

本系统是一个企业知识库问答项目。它使用有界 Agentic Workflow，而不是让模型无限反思。
LangGraph 负责状态、条件分支、检索重试、拒答和引用修复；模型只负责结构化查询规划、
基于证据生成，以及必要时的一次引用修复。

同一个 `thread_id` 的最近对话会通过 SQLite checkpointer 跨请求保存。当前实现支持持久化
多轮状态，但没有人工审批恢复控制台，也没有可恢复的后台任务队列。

## 混合检索

只使用向量检索并不够。向量检索擅长发现语义相似内容，却可能漏掉错误码、接口名、条款编号
和精确术语；SQLite FTS5 关键词检索适合精确匹配，却不擅长同义表达。

系统始终保留用户原始问题，并可生成少量互补查询。每个查询同时执行 Qdrant Dense Retrieval
和 SQLite FTS5 Sparse Retrieval，再使用加权 Reciprocal Rank Fusion（RRF）融合排名。
原始问题权重最高，自动查询权重递减，避免改写覆盖专有名词。

RRF 是排名融合信号，不是绝对相关性概率。没有 reranker 时，证据门控会检查 dense cosine
或 sparse token coverage，而不是因为某个结果排第一就认定它相关。

## Rerank

融合后的候选可交给 CrossEncoder reranker 二次排序。CrossEncoder 同时读取问题与候选片段，
通常比独立向量相似度更适合精排。默认模型输出按 logit 做固定 sigmoid 归一化；这只是稳定的
数值映射，不是统计校准。真正的阈值仍需要在人工标注的相关性数据集上调优。

如果 reranker 模型下载或加载失败，系统会回退到 fusion 排名，并使用独立的 dense/sparse
证据门控规则。

## 证据、引用与幻觉控制

系统通过多层机制降低无证据回答：

1. 证据不足时最多重新规划一次查询，仍不足就拒答。
2. 只有真正进入模型上下文的候选才会出现在 API `sources` 中。
3. 检索文档会被转义并放入不可信的 `<evidence>` 数据容器，文档中的命令不能作为系统指令。
4. 关键回答必须使用 `[S1]`、`[S2]` 等来源编号。
5. 服务端验证所有引用编号属于本轮上下文；缺失或越界时最多修复一次，再失败就拒答。

当前引用校验保证“编号存在且映射到本轮证据”，还不能保证每个 claim 都被引用文本语义蕴含。
因此项目不能声称完全消除幻觉，后续需要 claim-to-evidence 人工标注与语义评测。

## 幂等入库与双存储一致性

每个文档保存内容哈希和索引指纹。索引指纹包含切片参数、embedding 模型、collection 和 schema
版本；内容或指纹未变化且 Qdrant 向量数量完整时，重复导入才会跳过。

更新顺序是：

1. 写入新版本 Qdrant 向量。
2. 在一个 SQLite 事务中替换该文档的 chunks、FTS 和 manifest。
3. 最后尽力删除旧向量。

SQLite 是权威文本来源。Dense 命中必须回 SQLite 读取原文，所以清理失败产生的孤儿向量不会
进入模型上下文。

## API、UI 与 MCP

FastAPI 提供同步问答、节点级 SSE、安全上传、后台任务状态、来源列表和健康检查。Web UI
通过 SSE 展示 LangGraph 节点进度；当前不是 token-by-token 模型输出流。

普通聊天和上传可使用 `X-API-Key`。服务器本地路径导入与全局 reset 使用独立
`X-Admin-Key`，未配置 `ADMIN_API_KEY` 时该入口关闭。

MCP 服务只开放知识库搜索、问答和来源读取，不允许上传、reset 或任意服务器文件访问。

## 评测边界

仓库提供 Recall@5/10、MRR、nDCG@5/10 和检索延迟报告。样例评测集很小，只用于说明格式。
用于招聘简历前，应扩展为版本化资料和几十道人工标注问题，再比较 sparse-only、dense-only、
hybrid、hybrid + rerank 与 query planning 的消融结果。
