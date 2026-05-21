"""Router for web scraping endpoints.

This module handles HTTP requests for scraping web pages, crawling websites,
and chunking the extracted content for further processing.
"""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from src.utils.logger import get_logger

from .chunker import chunk_page
from .schemas import ScrapedPage, ScrapeRequest, ScrapeResponse
from .scraper import crawl

router = APIRouter(prefix="/scrape", tags=["scraper"])
logger = get_logger("scraper.router")


@router.post("", response_model=ScrapeResponse)
async def scrape(
    request: Request,
    scrape_req: ScrapeRequest,
) -> ScrapeResponse:
    """Scrape and chunk web pages starting from a seed URL.

    Crawls a website starting from the provided URL up to the specified depth,
    extracts product information, and chunks the page content.

    Args:
        scrape_req: Scrape request containing URL, depth limit, max pages, and link pattern.

    Returns:
        ScrapeResponse containing the seed URL, number of pages crawled, and extracted chunks.

    Raises:
        HTTPException: If the crawl operation fails (status 500).
    """
    store = request.app.state.vector_store
    seed_url = str(scrape_req.url)
    logger.info(
        f"Scrape request: url={seed_url} depth={scrape_req.depth} max_pages={scrape_req.max_pages}"
    )

    try:
        pages = await crawl(
            seed_url, scrape_req.depth, scrape_req.max_pages, scrape_req.link_pattern
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

    if all_chunks:
        upserted = await asyncio.to_thread(store.upsert_chunks, all_chunks)
        logger.info(f"Stored {upserted} chunks for {seed_url}")

    logger.info(f"Completed: {len(pages)} pages for {seed_url}")

    return ScrapeResponse(
        seed_url=seed_url, pages_crawled=len(pages), chunks=all_chunks
    )
