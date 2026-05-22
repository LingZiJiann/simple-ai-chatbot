from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from config.config import settings
from src.retrieval.router import router as retrieval_router
from src.scraper.router import router as scraper_router
from src.utils.logger import setup_logger
from src.vectorstore.store import VectorStore

setup_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.milvus_db_path).parent.mkdir(parents=True, exist_ok=True)
    store = VectorStore(settings.milvus_db_path)
    app.state.vector_store = store
    yield
    store.close()


app = FastAPI(title="Simple AI Chatbot API", version="0.1.0", lifespan=lifespan)
app.include_router(scraper_router, prefix="/api/v1")
app.include_router(retrieval_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
