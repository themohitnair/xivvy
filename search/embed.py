from fastembed.embedding import TextEmbedding
from models import PaperMetadata, PaperEntry
from typing import List

client = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=8, parallel=2)


class Embedder:
    def __init__(self):
        self.embedder = client

    def embed_batch(self, batch: List[PaperMetadata]) -> List[PaperEntry]:
        inputs = [f"{paper.title.strip()}\n{paper.abstract.strip()}" for paper in batch]

        embeddings = self.embedder.embed(inputs)

        entries: List[PaperEntry] = [
            PaperEntry(metadata=paper, vector=embedding)
            for paper, embedding in zip(batch, list(embeddings))
        ]

        return entries

    def embed_query(self, query: str):
        return list(self.embedder.embed([query]))[0]
