from qdrant_client import AsyncQdrantClient, models
from typing import List, Optional
import hashlib

from models import PaperEntry, SearchResult
from config import QDRANT_HOST, QDRANT_PORT

client = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


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
                    size=384,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    hnsw_config=models.HnswConfigDiff(m=0),
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=0,
                    memmap_threshold=5000,
                ),
            )

    async def enable_production_indexing(self):
        await self.client.update_collection(
            collection_name=self.collection_name,
            hnsw_config=models.HnswConfigDiff(
                m=8,
                payload_m=8,
                ef_construct=64,
                full_scan_threshold=10000,
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=10000,
            ),
        )

    async def upsert(self, entries: List[PaperEntry]):
        points: List[models.PointStruct] = []

        for entry in entries:
            payload = {
                "id": entry.metadata.id,
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
    ) -> List[SearchResult]:
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        search_results = []
        for point in results:
            payload = point.payload or {}
            search_results.append(
                SearchResult(
                    id=payload.get("id", ""),
                    score=point.score,
                )
            )

        return search_results

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, *args):
        await self.client.close()

    async def count_vectors(self) -> int:
        count = await self.client.count(self.collection_name)
        return count
