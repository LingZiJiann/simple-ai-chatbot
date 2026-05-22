"""Router for vector similarity search endpoints.

This module handles HTTP requests for semantic search over stored embeddings.
"""

import asyncio

from fastapi import APIRouter, Request

from src.utils.logger import get_logger

from .schemas import SearchRequest, SearchResponse, SearchResult

router = APIRouter(prefix="/retrieve", tags=["retrieval"])
logger = get_logger("retrieval.router")


@router.post("", response_model=SearchResponse)
async def retrieve(request: Request, search_req: SearchRequest) -> SearchResponse:
    """Search for chunks semantically similar to the query using cosine similarity.

    Embeds the query and finds the top-K most relevant chunks from the vector store.

    Args:
        search_req: Search request containing query text and top_k limit.

    Returns:
        SearchResponse with the query and ranked list of similar chunks.
    """
    store = request.app.state.vector_store
    logger.info(
        f"Retrieve request: query={search_req.query!r} top_k={search_req.top_k}"
    )

    raw = await asyncio.to_thread(store.search, search_req.query, search_req.top_k)
    results = [SearchResult(**r) for r in raw]

    return SearchResponse(query=search_req.query, results=results)
