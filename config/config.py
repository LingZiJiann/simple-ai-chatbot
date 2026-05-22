from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env")

    scraper_request_timeout: float = 10.0
    scraper_max_retries: int = 3
    scraper_retry_min_wait: float = 1.0
    scraper_retry_max_wait: float = 5.0
    scraper_politeness_delay: float = 1.0
    scraper_user_agent: str = "simple-ai-chatbot-scraper/0.1"
    scraper_default_depth: int = 2
    scraper_default_max_pages: int = 20
    milvus_db_path: str = "./data/milvus.db"
    api_base_url: str = "http://localhost:8000"


settings = Settings()
