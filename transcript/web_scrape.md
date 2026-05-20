# Transcript: FastAPI Web Scraper for RAG Ingestion

---

## 1. Requirements

**User:**
> I want to build a FastAPI endpoint for scraping webpage content for RAG ingestion.
>
> Requirements:
> 1. Create a POST endpoint that accepts a URL, optional crawl depth, optional max pages limit
> 2. Normalize the URL before scraping
> 3. Crawl pages recursively, default crawl depth set as 2, extract internal links from each page, follow only same-domain links, avoid revisiting previously crawled URLs
> 4. Parse and extract only headings and paragraphs
> 5. Convert extracted content into RAG chunks
> 6. Each chunk should contain heading, content and metadata
> 7. Metadata should include: source URL, normalized URL, page title
> 8. Add safeguards like max pages limit, request timeout, retry handling, rate limiting

---

## 2. Clarifications

Before planning, two open questions were raised:

**Q1 — Rate limiting scope:**
> "Rate limiting" could mean throttling outbound crawl requests (politeness toward external sites), protecting our own `/scrape` endpoint from excessive client calls, or both.

**Answer:** Crawl politeness only — throttle outbound requests per domain, no API-level rate limiting needed.

**Q2 — Chunk metadata structure:**
> Should the chunk metadata be a nested object `{ heading, content, metadata: { source_url, ... } }` or flat fields `{ heading, content, source_url, ... }`?

**Answer:** Nested metadata object, matching the stated requirement and cleaner for downstream RAG pipelines.

---

## 3. Iterative Refinements

### Adding `prod_desc` field

> "help me add an additional field for prod_desc: str and the scraper will need to find div id="product_description" and the description in `<p>`"

To capture product descriptions that live outside the normal heading/paragraph flow on e-commerce pages.

### Link pattern filtering

> "currently the scraper is appending any links found in the url, but now i only want a specific url to add to this queue instead of any links. For example when it's crawling this url `https://books.toscrape.com/catalogue/category/books/fantasy_19/index.html` i dont want it to crawl the category section, i only want it to crawl the catalogue like this `https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html`"

To avoid crawling category/navigation pages and only follow URLs that point to actual product pages.
