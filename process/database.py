import logging.config
from typing import List
import chromadb

from models import PaperToStore, SearchResults, PaperMetadata
from config import CHROMA_PORT, CHROMA_COLLECTION_NAME, LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)


def date_str_to_yyyymmdd_str(date_str: str) -> int:
    # Convert 'YYYY-MM-DD' to string 'YYYYMMDD'
    return int(date_str.replace("-", ""))


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
                "categories": ",".join(paper.categories),
                "date_published": date_str_to_yyyymmdd_str(paper.date_published),
            }
            for paper in batch
        ]

        self.logger.info(f"Inserting batch of {len(batch)} papers into collection...")

        await self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)

        self.logger.info("Batch insert complete.")

    async def search(
        self,
        embedding: List,
        top_k: int = 5,
        category_filters: List[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> SearchResults:
        filters = []

        if category_filters:
            if len(category_filters) > 1:
                category_filter = {
                    "$or": [
                        {"categories": {"$in": category.split(",")}}
                        for category in category_filters
                    ]
                }
            else:
                category_filter = {
                    "categories": {"$in": category_filters[0].split(",")}
                }
            filters.append(category_filter)

        if start_date:
            filters.append(
                {"date_published": {"$gte": date_str_to_yyyymmdd_str(start_date)}}
            )
        if end_date:
            filters.append(
                {"date_published": {"$lte": date_str_to_yyyymmdd_str(end_date)}}
            )

        where_filter = None
        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"$and": filters}

        results = await self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where_filter,
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
