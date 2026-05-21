import asyncio
import re
from collections import defaultdict, deque
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random

from config.config import settings
from src.utils.logger import get_logger

logger = get_logger("scraper")

_domain_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def normalize_url(url: str) -> str:
    """Normalize a URL to a canonical form.

    Converts scheme and domain to lowercase, removes fragments, and ensures
    trailing slashes are consistent.

    Args:
        url: The URL string to normalize.

    Returns:
        A normalized URL string.
    """
    parsed = urlparse(url)
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip("/") or "/",
        fragment="",
    )
    return urlunparse(normalized)


def _extract_internal_links(
    soup: BeautifulSoup,
    current_url: str,
    seed_domain: str,
    link_pattern: str | None = None,
) -> list[str]:
    """Extract internal links from a parsed HTML page.

    Finds all anchor tags and filters them to only include links that belong
    to the seed domain and optionally match a regex pattern.

    Args:
        soup: A BeautifulSoup object containing parsed HTML.
        current_url: The URL of the current page, used to resolve relative links.
        seed_domain: The domain to filter links by.
        link_pattern: Optional regex pattern to filter links by path.

    Returns:
        A list of normalized absolute URLs from the page.
    """
    compiled = re.compile(link_pattern) if link_pattern else None
    links = []
    for tag in soup.find_all("a", href=True):
        href = str(tag["href"]).strip()
        absolute = urljoin(current_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or parsed.netloc != seed_domain:
            continue
        if compiled and not compiled.search(parsed.path):
            continue
        links.append(absolute)
    return links


def _extract_page_data(soup: BeautifulSoup, url: str) -> dict:
    """Extract structured data from a parsed HTML page.

    Extracts page title, product description, price, and raw HTML from the
    given BeautifulSoup object.

    Args:
        soup: A BeautifulSoup object containing parsed HTML.
        url: The URL of the page being extracted.

    Returns:
        A dictionary containing:
            - html: Raw HTML string of the page.
            - url: The page URL.
            - page_title: Title extracted from <title> or <h1> tag.
            - prod_desc: Product description text.
            - price_gbp: Product price as a float.
    """
    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    page_title = (
        title_tag.get_text(strip=True)
        if title_tag
        else (h1_tag.get_text(strip=True) if h1_tag else url)
    )
    product_desc_div = soup.find("div", id="product_description")

    prod_desc = ""
    if product_desc_div:
        desc_p = product_desc_div.find_next_sibling("p")
        if desc_p:
            prod_desc = desc_p.get_text(strip=True)

    prod_price_div = soup.find("div", class_="product_price")
    prod_price = ""
    if prod_price_div:
        price_p = prod_price_div.find("p", class_="price_color")
        if price_p:
            prod_price = re.sub(r"[^0-9.]", "", price_p.get_text(strip=True))

    return {
        "html": str(soup),
        "url": url,
        "page_title": page_title,
        "prod_desc": prod_desc,
        "price_gbp": float(prod_price),
    }


@retry(
    stop=stop_after_attempt(settings.scraper_max_retries),
    wait=wait_random(
        min=settings.scraper_retry_min_wait, max=settings.scraper_retry_max_wait
    ),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    reraise=True,
)
async def _fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Fetch a URL with automatic retry logic.

    Makes an HTTP GET request with exponential backoff retry on transport and
    timeout errors.

    Args:
        client: An httpx AsyncClient instance.
        url: The URL to fetch.

    Returns:
        An httpx.Response object.

    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
        httpx.TransportError: If the request fails after max retries.
        httpx.TimeoutException: If the request times out after max retries.
    """
    response = await client.get(url, timeout=settings.scraper_request_timeout)
    response.raise_for_status()
    return response


async def _fetch_with_politeness(
    client: httpx.AsyncClient, url: str, domain: str
) -> httpx.Response:
    """Fetch a URL with politeness delays and domain-level rate limiting.

    Uses per-domain locks to ensure sequential requests to the same domain,
    with a configurable delay between requests to respect server resources.

    Args:
        client: An httpx AsyncClient instance.
        url: The URL to fetch.
        domain: The domain being fetched, used for lock management.

    Returns:
        An httpx.Response object.

    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
        httpx.TransportError: If the request fails after max retries.
        httpx.TimeoutException: If the request times out after max retries.
    """
    lock = _domain_locks[domain]
    async with lock:
        response = await _fetch_with_retry(client, url)
        await asyncio.sleep(settings.scraper_politeness_delay)
    return response


async def crawl(
    seed_url: str, depth: int, max_pages: int, link_pattern: str | None = None
) -> list[dict]:
    """Crawl a website starting from a seed URL up to a specified depth.

    Performs a breadth-first crawl of internal links, respecting politeness
    delays and domain-level rate limits. Extracts structured data (title,
    description, price) from each page.

    Args:
        seed_url: The starting URL for the crawl.
        depth: Maximum depth to crawl (0 = seed URL only, 1 = seed + first-level links).
        max_pages: Maximum number of pages to crawl before stopping.
        link_pattern: Optional regex pattern to filter links by path.

    Returns:
        A list of dictionaries containing extracted page data from each crawled URL.
        Each dictionary includes: html, url, page_title, prod_desc, and price_gbp.
    """
    seed_normalized = normalize_url(seed_url)
    seed_domain = urlparse(seed_normalized).netloc

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(seed_normalized, 0)])
    results: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.scraper_user_agent},
        follow_redirects=True,
    ) as client:
        while queue and len(visited) < max_pages:
            url, current_depth = queue.popleft()

            if url in visited:
                continue
            visited.add(url)

            try:
                response = await _fetch_with_politeness(client, url, seed_domain)
            except Exception as exc:
                logger.warning(f"Skipping {url}: {exc}")
                continue

            soup = BeautifulSoup(response.text, "lxml")
            page_data = _extract_page_data(soup, url)
            results.append(page_data)
            logger.info(f"Crawled [{current_depth}/{depth}] {url}")

            if current_depth < depth:
                for link in _extract_internal_links(
                    soup, url, seed_domain, link_pattern
                ):
                    normalized_link = normalize_url(link)
                    if normalized_link not in visited:
                        queue.append((normalized_link, current_depth + 1))

    return results
