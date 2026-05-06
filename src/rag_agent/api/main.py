
"""FastAPI HTTP 接口。

这个文件是项目的“后端服务入口”。
它把 RAG Agent 封装成 HTTP API，方便前端、Java 后端或其他系统调用。

常用接口：
- GET  /health：检查服务和索引状态。
- POST /ask：向 Agent 提问。
- POST /ingest：从服务器本地路径导入资料。
- POST /upload：上传文件并导入资料。
- GET  /sources：查看已经入库的文件来源。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from rag_agent.agent.graph import RAGAgent
from rag_agent.config import settings
from rag_agent.ingest.indexer import Indexer
from rag_agent.ingest.loaders import SUPPORTED_SUFFIXES
from rag_agent.retrieval.sqlite_store import SQLiteChunkStore

app = FastAPI(title="Mainstream RAG Agent", version="0.1.2")

# agent 在 startup 时初始化，避免每次请求都重新加载 embedding/reranker 模型。
agent: RAGAgent | None = None


class AskRequest(BaseModel):
    """/ask 请求体。"""

    question: str = Field(..., min_length=1, description="用户问题")


class IngestRequest(BaseModel):
    """/ingest 请求体。"""

    path: str = "data/raw"
    reset: bool = False


@app.on_event("startup")
def startup() -> None:
    """服务启动时初始化 Agent。"""

    global agent
    agent = RAGAgent()


@app.get("/health")
def health() -> dict:
    """健康检查接口。"""

    store = SQLiteChunkStore(settings.sqlite_path)
    return {"status": "ok", "chunks": store.count(), "collection": settings.qdrant_collection}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    """问答接口。"""

    assert agent is not None
    return agent.ask(req.question)


@app.post("/ingest")
def ingest(req: IngestRequest) -> dict:
    """从本地路径导入文档。"""

    indexer = Indexer()
    return indexer.ingest_path(req.path, reset=req.reset)


@app.post("/upload")
async def upload_and_ingest(
    files: Annotated[list[UploadFile], File(description="上传 PDF / Word / Markdown / TXT / HTML 文件")],
    reset: Annotated[bool, Form(description="是否清空旧索引后重新导入")] = False,
) -> dict:
    """上传文件并立即导入索引。

    这个接口让项目更像真实知识库系统：
    用户不需要登录服务器执行 CLI，只需要通过 HTTP 上传资料即可。
    """

    upload_dir = Path("data/raw/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for file in files:
        # Path(...).name 可以去掉路径，防止有人上传 ../../xxx 这种危险文件名。
        filename = Path(file.filename or "uploaded.txt").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        target = upload_dir / filename
        content = await file.read()
        target.write_bytes(content)
        saved_files.append(str(target))

    result = Indexer().ingest_path(upload_dir, reset=reset)
    result["uploaded_files"] = saved_files
    return result


@app.get("/sources")
def sources() -> dict:
    """查看每个来源文件导入了多少个 chunk。"""

    store = SQLiteChunkStore(settings.sqlite_path)
    return {"sources": store.list_sources()}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "rag_agent.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir="src",
    )
