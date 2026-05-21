from fastapi import APIRouter, HTTPException

from src.utils.logger import get_logger

from .chunker import chunk_page
from .schemas import ScrapedPage, ScrapeRequest, ScrapeResponse
from .scraper import crawl

router = APIRouter(prefix="/scrape", tags=["scraper"])
logger = get_logger("scraper.router")


@router.post("", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    seed_url = str(request.url)
    logger.info(
        f"Scrape request: url={seed_url} depth={request.depth} max_pages={request.max_pages}"
    )

    try:
        pages = await crawl(
            seed_url, request.depth, request.max_pages, request.link_pattern
        )
    except Exception as exc:
        logger.error(f"Crawl failed for {seed_url}: {exc}")
        raise HTTPException(status_code=500, detail=f"Crawl failed: {exc}") from exc

    all_chunks = []
    for p in pages:
        scraped = ScrapedPage(
            url=p["url"],
            page_title=p["page_title"],
            prod_desc=p["prod_desc"],
            price_gbp=p.get("price_gbp"),
        )
        all_chunks.extend(chunk_page(scraped))

    logger.info(f"Completed: {len(pages)} pages for {seed_url}")

    return ScrapeResponse(
        seed_url=seed_url, pages_crawled=len(pages), chunks=all_chunks
    )
