# Changelog

## Unreleased

### Added

- 资料 manifest 新增持久化展示名，上传哈希前缀不再出现在资料库和后续引用中。
- 新增受管资料删除 API：事务清理 SQLite/FTS，并补偿清理 Qdrant 与上传副本。
- Web UI 新增站内删除确认、多选/全选批量删除、逐行忙碌状态与失败恢复。
- 离线评测新增证据门控的误拒答率、错误放行率与回答/拒答 Precision/Recall。
- OpenAI-compatible 推理模型新增显式 thinking 控制与空输出/截断诊断。

### Changed

- Web UI 重构为轻量白色文档工作台，统一字号阶梯、三栏比例和移动端触控尺寸。
- `/api/v1/sources` 改为浏览器安全视图，不再暴露绝对路径、原始错误或索引指纹。
- 证据门控改为 reranker、dense、sparse 三路绝对信号的可解释 `ANY` 策略，避免单一
  CrossEncoder 分数错误否决强词法或向量证据。
- 查询规划失败时使用确定性清单意图扩展，并区分证据不足、模型生成失败和引用失败。

## 1.0.0 — 2026-07-26

### Added

- 有界自适应 LangGraph：多查询规划、证据重试、拒答和一次引用修复。
- SQLite checkpoint 持久化多轮状态与节点级 SSE。
- OpenAI Responses API 默认路径和 Chat Completions 兼容路径。
- Weighted RRF、独立分数校准、检索降级和透明 debug 信号。
- 服务端引用编号校验、检索内容转义和 Prompt Injection 风险标签。
- 文档 manifest、内容哈希、幂等增量入库、原子 SQLite 替换和旧向量清理。
- 强制密钥上传、独立管理员密钥、限定路径导入、后台任务与 ready/live 健康检查。
- 零构建 Web UI、只读 MCP server、Dockerfile、CI、pre-commit 与 MIT License。
- Recall@K、MRR、nDCG 和延迟评测，以及覆盖核心失败路径的离线测试。

### Changed

- Qdrant 镜像和 Python 依赖使用有界版本，不再使用无上限依赖或 `latest`。
- FastAPI 生命周期迁移到 lifespan，并复用检索/入库资源。
- Markdown、DOCX 和文本解析保留更完整的标题、表格和来源元数据。
- CLI 输出与当前 API 来源结构对齐。

### Migration

- 旧版 SQLite chunk 没有稳定 `document_id`，升级启动时会记录 warning 并清理这些无法安全迁移的派生索引行。升级后请重新运行一次 `scripts/ingest.py`；原始资料不会被删除。
- 索引指纹、切片身份与 Qdrant schema 契约均已升级，已有 collection 建议使用 `--reset` 明确重建。

### Security

- 删除未限定的任意服务器路径读取边界。
- 增加上传大小、数量、文件名、空文件和基础 magic bytes 校验。
- Qdrant 和 API 的 Docker 端口默认只绑定本机回环地址。
- MCP 仅开放只读能力。
