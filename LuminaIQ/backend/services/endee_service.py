"""
Endee vector database service — drop-in replacement for qdrant_service.py.

Key design choices:
- Deterministic chunk IDs: "{document_id}:{chunk_index}"
  Allows fetch/clone/delete by ID since we can delete by filter via
  Index.delete_with_filter({"document_id": doc_id}).
- All SDK calls are synchronous; wrapped with run_in_executor so
  they never block the async event loop.
- Automatic retry with exponential backoff for transient failures.
- Indexes (≈ Qdrant collections) are created on demand per project:
  name = "project_{project_id}"

Endee SDK notes (verified against endee 0.1.25):
  - Endee(token=None)           → no-auth mode
  - client.create_index(name, dimension, space_type, precision=Precision.FLOAT32)
  - client.get_index(name)      → Index object
  - client.list_indexes()       → list of index metadata objects
  - index.upsert([{id, vector, meta, filter}])    → filter is plain dict
  - index.query(vector, top_k, filter=[{key:{$op:val}}])  → filter is LIST of dicts
  - index.delete_with_filter({"document_id": "..."})      → filter is plain dict
  - index.delete_vector(id)
  - index.get_vector(id)
"""

import asyncio
from typing import List, Dict, Any, Optional

from endee import Endee, Precision
from config.settings import settings
from utils.logger import logger


# ── helpers ──────────────────────────────────────────────────────────────────

def _chunk_id(document_id: str, chunk_index: int) -> str:
    """Stable vector ID used in Endee for a given chunk."""
    return f"{document_id}:{chunk_index}"


async def _run(fn, *args, **kwargs):
    """Run a synchronous Endee SDK call off the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ─────────────────────────────────────────────────────────────────────────────

class EndeeService:
    """
    Endee vector database service — async wrapper over the synchronous SDK.

    Public interface mirrors QdrantService so all callers can swap the import
    without touching their logic:
        create_collection  →  ensure index exists
        upsert_chunks      →  batch upsert into index
        search             →  ANN query with optional doc filter
        get_initial_chunks →  fetch first N chunks by deterministic ID
        delete_vectors     →  delete all vectors for a document
        clone_document_vectors →  copy vectors between indexes
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0   # seconds
    UPSERT_BATCH = 500        # Endee max is 1 000; stay conservative

    def __init__(self):
        kwargs: Dict[str, Any] = {}
        if settings.ENDEE_AUTH_TOKEN:
            kwargs["token"] = settings.ENDEE_AUTH_TOKEN

        self._client = Endee(**kwargs)

        # SDK's base_url already includes /api/v1 (default: http://127.0.0.1:8080/api/v1)
        # Override if ENDEE_URL points to a different host/port.
        configured_url = settings.ENDEE_URL.rstrip("/")
        sdk_api_url = f"{configured_url}/api/v1"
        self._client.set_base_url(sdk_api_url)

        logger.info(
            f"[EndeeService] Initialized | url={sdk_api_url} "
            f"auth={'yes' if settings.ENDEE_AUTH_TOKEN else 'no'}"
        )

    # ── Index management ─────────────────────────────────────────────────────

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = None,
    ):
        """Create Endee index if it does not already exist (async)."""
        vector_size = vector_size or settings.EMBEDDING_DIMENSION
        try:
            # list_indexes() returns a list of IndexMetadata objects
            indexes = await _run(self._client.list_indexes)
            existing = {idx.name for idx in (indexes or [])}

            if collection_name not in existing:
                await _run(
                    self._client.create_index,
                    name=collection_name,
                    dimension=vector_size,
                    space_type="cosine",
                    precision=Precision.FLOAT32,
                )
                logger.info(f"[EndeeService] Created index: {collection_name}")
            else:
                logger.debug(f"[EndeeService] Index already exists: {collection_name}")

        except Exception as e:
            logger.error(f"[EndeeService] Error creating index {collection_name}: {e}")
            raise

    # ── Write ────────────────────────────────────────────────────────────────

    async def upsert_chunks(
        self,
        collection_name: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ):
        """
        Upsert chunks into the given index with retry + exponential backoff.

        ID scheme: "{document_id}:{chunk_index}"

        Endee upsert item format:
          {
            "id":     str,
            "vector": list[float],
            "meta":   {text, document_id, document_name, chunk_id},  # queryable via index.query
            "filter": {document_id, document_name}   # used by delete_with_filter & query filter
          }

        NOTE: "filter" in upsert is a PLAIN dict (not a list).
              "filter" in query is a LIST of dicts with $eq/$in ops.
        """
        records = []
        for chunk, embedding, meta in zip(chunks, embeddings, metadata):
            doc_id = meta.get("document_id", "")
            chunk_idx = meta.get("chunk_id", 0)
            records.append({
                "id": _chunk_id(doc_id, chunk_idx),
                "vector": embedding,
                "meta": {
                    "text": chunk,
                    "document_id": doc_id,
                    "document_name": meta.get("document_name", ""),
                    "chunk_id": chunk_idx,
                },
                # plain dict — used by delete_with_filter and query pre-filter
                "filter": {
                    "document_id": doc_id,
                    "document_name": meta.get("document_name", ""),
                },
            })

        index = await _run(self._client.get_index, name=collection_name)

        for batch_start in range(0, len(records), self.UPSERT_BATCH):
            batch = records[batch_start: batch_start + self.UPSERT_BATCH]
            last_err = None
            for attempt in range(self.MAX_RETRIES):
                try:
                    await _run(index.upsert, batch)
                    logger.info(
                        f"[EndeeService] Upserted {len(batch)} chunks "
                        f"(offset {batch_start}) → {collection_name}"
                    )
                    break
                except Exception as e:
                    last_err = e
                    err_str = str(e).lower()
                    is_retryable = any(
                        x in err_str
                        for x in ["timeout", "timed out", "connection",
                                   "temporary", "unavailable", "reset"]
                    )
                    if is_retryable and attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(
                            f"[EndeeService] Upsert retry {attempt+1}/{self.MAX_RETRIES} "
                            f"in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[EndeeService] Upsert failed: {e}")
                        raise
            if last_err is not None and attempt == self.MAX_RETRIES - 1:
                raise last_err

    # ── Read / Search ────────────────────────────────────────────────────────

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        ANN search with optional document_id filter (async).

        filter_conditions = {"document_ids": ["id1", "id2", ...]}

        NOTE: query(filter=...) expects a LIST of dicts with $eq/$in operators:
              [{"document_id": {"$eq": "id1"}}]
        """
        try:
            index = await _run(self._client.get_index, name=collection_name)

            query_kwargs: Dict[str, Any] = {
                "vector": query_vector,
                "top_k": limit,
                "include_vectors": False,
            }

            if filter_conditions and filter_conditions.get("document_ids"):
                doc_ids = filter_conditions["document_ids"]
                if len(doc_ids) == 1:
                    query_kwargs["filter"] = [
                        {"document_id": {"$eq": doc_ids[0]}}
                    ]
                else:
                    query_kwargs["filter"] = [
                        {"document_id": {"$in": doc_ids}}
                    ]

            results = await _run(index.query, **query_kwargs)

            hits = []
            for item in results:
                meta = item.get("meta") or {}
                hits.append({
                    "id": item["id"],
                    "score": item.get("similarity", 0.0),
                    "text": meta.get("text", ""),
                    "document_id": meta.get("document_id"),
                    "chunk_id": meta.get("chunk_id"),
                })

            logger.debug(f"[EndeeService] Found {len(hits)} results in {collection_name}")
            return hits

        except Exception as e:
            err = str(e)
            if "not found" in err.lower() or "doesn't exist" in err.lower():
                logger.warning(
                    f"[EndeeService] Index {collection_name} not found during search — returning []"
                )
                return []
            logger.error(f"[EndeeService] Search error: {e}")
            raise

    async def get_initial_chunks(
        self,
        collection_name: str,
        document_id: str,
        limit: int = 10,
    ) -> List[str]:
        """
        Fetch the first `limit` chunks for a document by deterministic ID.
        IDs are {document_id}:0 … {document_id}:{limit-1}.
        """
        try:
            index = await _run(self._client.get_index, name=collection_name)
            texts: List[str] = []
            for i in range(limit):
                vid = _chunk_id(document_id, i)
                try:
                    item = await _run(index.get_vector, vid)
                    if item:
                        meta = item.get("meta") or {}
                        text = meta.get("text", "")
                        if text:
                            texts.append(text)
                        else:
                            break
                    else:
                        break
                except Exception:
                    break
            return texts

        except Exception as e:
            err = str(e)
            if "not found" in err.lower() or "doesn't exist" in err.lower():
                return []
            logger.error(f"[EndeeService] get_initial_chunks error: {e}")
            return []

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_vectors(self, collection_name: str, document_id: str):
        """
        Delete all vectors for a document using Index.delete_with_filter().

        delete_with_filter(filter) takes a plain dict:
            {"document_id": "abc123"}
        This deletes every vector whose stored filter.document_id matches.
        """
        try:
            index = await _run(self._client.get_index, name=collection_name)
            result = await _run(
                index.delete_with_filter,
                {"document_id": document_id},
            )
            logger.info(
                f"[EndeeService] Deleted vectors for document {document_id} "
                f"from {collection_name}: {result}"
            )

        except Exception as e:
            err = str(e)
            if "not found" in err.lower() or "doesn't exist" in err.lower():
                logger.warning(
                    f"[EndeeService] Index {collection_name} not found during delete — skipping"
                )
                return
            logger.error(f"[EndeeService] delete_vectors error: {e}")

    # ── Clone ────────────────────────────────────────────────────────────────

    async def clone_document_vectors(
        self,
        source_collection: str,
        target_collection: str,
        source_document_id: str,
        target_document_id: str,
        target_document_name: str,
        batch_size: int = 100,
    ) -> int:
        """
        Clone all vectors for a document from one index to another.

        Used by book imports to skip re-embedding (fast path).
        Returns the number of vectors cloned (0 if source not found).
        """
        try:
            src_index = await _run(self._client.get_index, name=source_collection)
            tgt_index = await _run(self._client.get_index, name=target_collection)
        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(
                    f"[VectorClone] Source index {source_collection} not found — "
                    "falling back to re-embedding"
                )
                return 0
            raise

        total_cloned = 0
        i = 0

        while True:
            # Fetch a batch of chunks by deterministic ID
            batch_records = []
            for j in range(i, i + batch_size):
                vid = _chunk_id(source_document_id, j)
                try:
                    item = await _run(src_index.get_vector, vid)
                    if item and item.get("vector"):
                        batch_records.append((j, item))
                    else:
                        break
                except Exception:
                    break

            if not batch_records:
                break

            # Rewrite IDs, document_id, document_name
            new_records = []
            for chunk_idx, item in batch_records:
                new_meta = dict(item.get("meta") or {})
                new_meta["document_id"] = target_document_id
                new_meta["document_name"] = target_document_name
                new_records.append({
                    "id": _chunk_id(target_document_id, chunk_idx),
                    "vector": item["vector"],
                    "meta": new_meta,
                    "filter": {
                        "document_id": target_document_id,
                        "document_name": target_document_name,
                    },
                })

            await _run(tgt_index.upsert, new_records)
            total_cloned += len(new_records)
            logger.info(
                f"[VectorClone] {total_cloned} vectors cloned so far "
                f"({source_collection}/{source_document_id} → "
                f"{target_collection}/{target_document_id})"
            )

            if len(batch_records) < batch_size:
                break
            i += batch_size

        logger.info(
            f"[VectorClone] Complete: {total_cloned} vectors → "
            f"{target_collection}/{target_document_id}"
        )
        return total_cloned

    # ── LangChain compatibility shim ─────────────────────────────────────────

    def get_vector_store(self, collection_name: str):  # pragma: no cover
        raise NotImplementedError(
            "get_vector_store() is no longer supported. "
            "Use EndeeRetriever from rag_service instead."
        )


endee_service = EndeeService()
