# Contributing

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev,mcp]"
.\.venv\Scripts\pre-commit install
```

不要提交 `.env`、API Key、私有资料、模型缓存、SQLite 数据库或评测报告中的敏感内容。

## 提交前检查

```powershell
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .
.\.venv\Scripts\pytest --cov=rag_agent --cov-report=term-missing
```

如果修改检索、切片、embedding、reranker、阈值或 Prompt，还应在同一版本化数据集上运行：

```powershell
.\.venv\Scripts\python scripts/eval_retrieval.py --output-dir reports
```

提交 PR 时说明：

- 问题和设计动机。
- 关键取舍与不做的内容。
- 新增或修改的测试。
- 评测数据集版本和 before/after 原始指标；没有评测时明确写“未评测”。
- 是否改变索引 schema、环境变量、API 合同或安全边界。

不要用个别手工问题的表现声称整体准确率提升。
