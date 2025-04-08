from qdrant_client import AsyncQdrantClient, models
from models import PaperEntry
from typing import List, Optional
import hashlib

client = AsyncQdrantClient(host="localhost", port="6333")


class Database:
    def __init__(self):
        self.client = client
        self.collection_name = "xivvy"

    def generate_point_id(self, arxiv_id: str) -> int:
        return int(hashlib.sha256(arxiv_id.encode()).hexdigest(), 16) % (2**63)

    async def initialize(self):
        exists = await self.client.collection_exists(self.collection_name)

        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384, distance=models.Distance.COSINE, on_disk=True
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=16,
                    payload_m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=2000000,
                    memmap_threshold=100000,
                ),
            )

    async def upsert(self, entries: List[PaperEntry]):
        points: List[models.PointStruct] = []

        for entry in entries:
            payload = {
                "id": entry.metadata.id,
                "abstract": entry.metadata.abstract,
                "title": entry.metadata.title,
            }
            points.append(
                models.PointStruct(
                    id=self.generate_point_id(entry.metadata.id),
                    vector=entry.vector,
                    payload=payload,
                )
            )

        await self.client.upsert(collection_name=self.collection_name, points=points)

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[models.Filter] = None,
    ) -> List[models.ScoredPoint]:
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        return results

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        await self.client.close()
