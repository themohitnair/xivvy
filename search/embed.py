from fastembed.embedding import TextEmbedding
from typing import List
import asyncio

from models import PaperMetadata, PaperEntry
from config import EMBEDDING_MODEL, NUMBER_OF_PARALLEL_PROCESSES, NUMBER_OF_THREADS

client = TextEmbedding(
    model_name=EMBEDDING_MODEL,
    threads=NUMBER_OF_THREADS,
    parallel=NUMBER_OF_PARALLEL_PROCESSES,
)


class Embedder:
    def __init__(self):
        self.embedder = client

    def truncate_text(self, text: str, max_chars: int = 512):
        return text[:max_chars]

    async def embed_batch(self, batch: List[PaperMetadata]) -> List[PaperEntry]:
        return await asyncio.to_thread(self._embed_sync, batch)

    def _embed_sync(self, batch: List[PaperMetadata]) -> List[PaperEntry]:
        inputs = [
            f"{paper.title.strip()}\n{self.truncate_text(text=paper.abstract.strip(), max_chars=512)}"
            for paper in batch
        ]
        embeddings = list(self.embedder.embed(inputs))

        return [
            PaperEntry(metadata=paper, vector=embedding)
            for paper, embedding in zip(batch, embeddings)
        ]

    def embed_query(self, query: str):
        return list(self.embedder.embed([query]))[0]
