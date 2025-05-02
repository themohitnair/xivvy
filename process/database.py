from typing import List
import chromadb
from config import CHROMA_PORT, CHROMA_COLLECTION_NAME, LOG_CONFIG
import logging.config
from typing import Optional, Dict

from models import PaperToStore, SearchResults

logging.config.dictConfig(LOG_CONFIG)


class Database:
    def __init__(self):
        self.client = None
        self.collection = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        self.logger.info("Initializing ChromaDB Client...")
        self.client = await chromadb.AsyncHttpClient(host="localhost", port=CHROMA_PORT)
        self.logger.info("ChromaDB Client Initialized.")

        self.logger.info("Creating collection if it doesn't exist...")
        self.collection = await self.client.get_or_create_collection(
            CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        self.logger.info("Created collection.")

    async def insert_batch(self, batch: List[PaperToStore]):
        ids = [paper.id for paper in batch]
        embeddings = [paper.embedding for paper in batch]
        metadatas = [
            {
                "categories": ",".join(paper.categories)
                if isinstance(paper.categories, list)
                else paper.categories,
                "date_published": paper.date_published,
            }
            for paper in batch
        ]

        self.logger.info(f"Inserting batch of {len(batch)} papers into collection...")

        await self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)

        self.logger.info("Batch insert complete.")

    async def search(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, str]] = None,
    ):
        self.logger.info(f"Running search (top_k={top_k}, filter={filter})...")

        results = await self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=filter,
        )

        matches = [
            {"id": id_, "distance": distance, "metadata": metadata}
            for id_, distance, metadata in zip(
                results["ids"][0], results["distances"][0], results["metadatas"][0]
            )
        ]

        self.logger.info(f"Search returned {len(matches)} results.")

        return SearchResults(results=matches)
