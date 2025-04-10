from fastembed.embedding import TextEmbedding
from models import PaperMetadata, PaperEntry
from typing import List
import asyncio

client = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=12, parallel=1)


class Embedder:
    def __init__(self):
        self.embedder = client

    async def embed_batch(self, batch: List[PaperMetadata]) -> List[PaperEntry]:
        return await asyncio.to_thread(self._embed_sync, batch)

    def _embed_sync(self, batch: List[PaperMetadata]) -> List[PaperEntry]:
        inputs = [f"{paper.title.strip()}\n{paper.abstract.strip()}" for paper in batch]
        embeddings = list(self.embedder.embed(inputs))

        return [
            PaperEntry(metadata=paper, vector=embedding)
            for paper, embedding in zip(batch, embeddings)
        ]

    def embed_query(self, query: str):
        return list(self.embedder.embed([query]))[0]
