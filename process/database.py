import logging.config
from typing import List
import chromadb

from models import PaperToStore, SearchResults, PaperMetadata
from config import CHROMA_PORT, CHROMA_COLLECTION_NAME, LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)


class Database:
    def __init__(self):
        self.client = None
        self.collection = None
        self.logger = logging.getLogger(__name__)
        self.collection_name = CHROMA_COLLECTION_NAME

    async def initialize(self):
        self.logger.info("Initializing ChromaDB Client...")
        self.client = await chromadb.AsyncHttpClient(host="localhost", port=CHROMA_PORT)
        self.logger.info("ChromaDB Client Initialized.")

        self.logger.info("Creating collection if it doesn't exist...")
        self.collection = await self.client.get_or_create_collection(
            self.collection_name, metadata={"hnsw:space": "cosine"}
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

    async def search(self, embedding: list, top_k: int = 5) -> SearchResults:
        results = await self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        matches = [
            {
                "id": id_,
                "distance": distance,
                "metadata": PaperMetadata(
                    categories=[
                        cat.strip()
                        for cat in metadata["categories"].split(",")
                        if cat.strip()
                    ],
                    date_published=metadata["date_published"],
                ),
            }
            for id_, distance, metadata in zip(
                results["ids"][0], results["distances"][0], results["metadatas"][0]
            )
        ]

        return SearchResults(
            results=[
                {**match, "metadata": match["metadata"].model_dump()}
                for match in matches
            ]
        )
