from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    url: str = Field(
        default="https://books.toscrape.com/catalogue/category/books/travel_2/index.html"
    )
    depth: int = Field(default=2, ge=0, le=10)
    max_pages: int = Field(default=5, ge=1, le=500)
    link_pattern: str | None = Field(
        default=r"^/catalogue/(?!category)",
        description="Regex applied to the URL path of discovered links. Only matching links are queued.",
    )


class ScrapedPage(BaseModel):
    url: str
    page_title: str
    prod_desc: str
    price_gbp: float | None = None


class Chunk(BaseModel):
    chunk_id: str
    source_url: str
    chunk_index: int = Field(ge=0)
    text: str
    char_count: int
    page_title: str
    price_gbp: float | None = None


class ScrapeResponse(BaseModel):
    seed_url: str
    pages_crawled: int
    chunks: list[Chunk] = Field(default_factory=list)
