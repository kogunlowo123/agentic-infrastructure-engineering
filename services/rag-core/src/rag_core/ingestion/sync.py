"""Sync job orchestrating the full ingestion pipeline."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Iterator

from .loader_registry import Document, LoaderRegistry
from ..chunking.base import Chunk
from ..chunking.code_aware import TerraformHCLChunker
from ..chunking.recursive import RecursiveChunker
from ..embeddings.base import EmbeddingModel
from ..enrichment.metadata import MetadataExtractor
from ..stores.vector_base import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Statistics from a sync job run."""

    documents_processed: int = 0
    chunks_created: int = 0
    chunks_upserted: int = 0
    errors: int = 0
    skipped: int = 0
    error_messages: list[str] = field(default_factory=list)


class SyncJob:
    """Orchestrates: load -> chunk -> enrich -> embed -> store."""

    BATCH_SIZE = 64

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self._embedder = embedding_model
        self._store = vector_store
        self._tf_chunker = TerraformHCLChunker(chunk_size=1024)
        self._text_chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._registry = LoaderRegistry()
        self._metadata_extractor = MetadataExtractor()

    def run_from_documents(self, documents: Iterator[Document]) -> SyncStats:
        """Run ingestion pipeline for a stream of documents.

        Args:
            documents: Iterator of Document objects to ingest.

        Returns:
            SyncStats with processing results.
        """
        stats = SyncStats()
        batch_ids: list[str] = []
        batch_contents: list[str] = []
        batch_metadatas: list[dict] = []

        def flush_batch() -> None:
            if not batch_contents:
                return
            try:
                embeddings = self._embedder.embed(batch_contents)
                self._store.upsert(
                    chunk_ids=batch_ids,
                    contents=batch_contents,
                    embeddings=embeddings,
                    metadatas=batch_metadatas,
                )
                stats.chunks_upserted += len(batch_contents)
            except Exception as exc:
                stats.errors += 1
                stats.error_messages.append(str(exc))
                logger.error("Batch upsert failed: %s", exc)
            finally:
                batch_ids.clear()
                batch_contents.clear()
                batch_metadatas.clear()

        for doc in documents:
            try:
                chunks = self._chunk_document(doc)
                enriched = self._enrich_chunks(chunks, doc)

                for chunk in enriched:
                    batch_ids.append(chunk.chunk_id)
                    batch_contents.append(chunk.content)
                    batch_metadatas.append(chunk.metadata)
                    stats.chunks_created += 1

                    if len(batch_contents) >= self.BATCH_SIZE:
                        flush_batch()

                stats.documents_processed += 1
            except Exception as exc:
                stats.errors += 1
                stats.error_messages.append(f"{doc.source}: {exc}")
                logger.error("Failed to process document %s: %s", doc.source, exc)

        flush_batch()
        logger.info(
            "Sync complete: docs=%d, chunks=%d, upserted=%d, errors=%d",
            stats.documents_processed,
            stats.chunks_created,
            stats.chunks_upserted,
            stats.errors,
        )
        return stats

    def _chunk_document(self, doc: Document) -> list[Chunk]:
        """Select appropriate chunker based on document type."""
        file_type = doc.metadata.get("file_type", "")
        if file_type == "terraform" or doc.metadata.get("extension", "") in (".tf", ".hcl"):
            return self._tf_chunker.chunk(doc.content, doc.metadata)
        return self._text_chunker.chunk(doc.content, doc.metadata)

    def _enrich_chunks(self, chunks: list[Chunk], doc: Document) -> list[Chunk]:
        """Add additional metadata to chunks."""
        enriched = []
        for chunk in chunks:
            chunk.metadata["source"] = doc.source
            chunk.metadata.setdefault("doc_id", str(uuid.uuid5(uuid.NAMESPACE_URL, doc.source)))
            enriched.append(chunk)
        return enriched
