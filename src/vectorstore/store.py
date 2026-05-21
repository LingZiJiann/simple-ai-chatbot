import logging
from typing import TYPE_CHECKING

from pymilvus import DataType, MilvusClient
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from src.scraper.schemas import Chunk

logger = logging.getLogger("vectorstore")

COLLECTION_NAME = "chunks"
_DIM = 384
_PRICE_NULL = -1.0


class VectorStore:
    """Milvus Lite vector store wrapper with embedding support."""

    def __init__(self, db_path: str) -> None:
        self._client = MilvusClient(db_path)
        self._model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection with schema and COSINE flat index if not exists."""
        if self._client.has_collection(COLLECTION_NAME):
            return

        schema = self._client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=16, is_primary=True)
        schema.add_field("source_url", DataType.VARCHAR, max_length=2048)
        schema.add_field("chunk_index", DataType.INT64)
        schema.add_field("text", DataType.VARCHAR, max_length=1024)
        schema.add_field("char_count", DataType.INT64)
        schema.add_field("page_title", DataType.VARCHAR, max_length=512)
        schema.add_field("price_gbp", DataType.FLOAT)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=_DIM)

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="vector", metric_type="COSINE", index_type="FLAT"
        )

        self._client.create_collection(
            collection_name=COLLECTION_NAME, schema=schema, index_params=index_params
        )
        logger.info("Created Milvus collection '%s'", COLLECTION_NAME)

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Embed and upsert chunks. Returns number of rows written.

        This method is synchronous — call via asyncio.to_thread from async code.
        """
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        vectors = self._model.encode(texts, convert_to_tensor=False)

        rows = [
            {
                "chunk_id": c.chunk_id,
                "source_url": c.source_url,
                "chunk_index": c.chunk_index,
                "text": c.text[:1024],
                "char_count": c.char_count,
                "page_title": c.page_title[:512],
                "price_gbp": c.price_gbp if c.price_gbp is not None else _PRICE_NULL,
                "vector": vectors[i].tolist(),
            }
            for i, c in enumerate(chunks)
        ]

        result = self._client.upsert(collection_name=COLLECTION_NAME, data=rows)
        count = result.get("upsert_count", len(rows))
        logger.info("Upserted %d chunks into '%s'", count, COLLECTION_NAME)
        return count

    def close(self) -> None:
        """Close the Milvus client connection."""
        self._client.close()
