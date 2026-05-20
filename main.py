from fastapi import FastAPI

from src.scraper.router import router as scraper_router
from src.utils.logger import setup_logger

setup_logger("app")

app = FastAPI(title="Simple AI Chatbot API", version="0.1.0")
app.include_router(scraper_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
