from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: str
    source_url: str
    chunk_index: int
    text: str
    char_count: int
    page_title: str
    price_gbp: float | None
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
