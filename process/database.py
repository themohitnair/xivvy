import logging.config
import socket
from qdrant_client import AsyncQdrantClient, models
from typing import List, Optional

from config import DB_COLLECTION_NAME, DB_PORT, LOG_CONFIG
from models import ArxivDomains, StoredPaper, SearchResult, PaperMetadata
from process.embed import Embedder
from utils import string_to_uuid, iso_date_to_unix, unix_to_iso

logging.config.dictConfig(LOG_CONFIG)


class Database:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.client = AsyncQdrantClient(url=f"http://localhost:{DB_PORT}")
        self.logger.info("Connected to port 6333 (Qdrant Database).")
        self.collection_name = DB_COLLECTION_NAME
        self.embedder = Embedder()

    def is_server_running(self) -> bool:
        host = "localhost"
        port = DB_PORT

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((host, port))
                self.logger.info(f"Qdrant server is running on {host}:{port}")
                return True
            except (ConnectionRefusedError, socket.timeout):
                self.logger.warning(f"Qdrant server not accessible at {host}:{port}")
                return False

    async def create_collection_if_not_exists(self) -> bool:
        if not self.is_server_running():
            self.logger.error("Cannot create collection: Qdrant server is not running")
            return False

        try:
            collection_exists = await self.client.collection_exists(
                self.collection_name
            )
            if collection_exists:
                self.logger.info("Collection found.")
                return True
            else:
                self.logger.info("Collection not found.")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=768, distance=models.Distance.COSINE
                    ),
                )
                self.logger.info("Created the collection.")
                return True
        except Exception as e:
            self.logger.error(f"Error creating collection: {str(e)}")
            return False

    async def insert_batch(self, batch: List[StoredPaper]) -> bool:
        if not self.is_server_running():
            self.logger.error("Cannot insert batch: Qdrant server is not running")
            return False

        if not batch:
            self.logger.warning("No papers to insert in batch")
            return False

        points = []
        for paper in batch:
            point = models.PointStruct(
                id=str(string_to_uuid(paper.paper_id)),
                payload={
                    "id": paper.paper_id,
                    "categories": [cat.value for cat in paper.categories],
                    "date_updated": iso_date_to_unix(paper.date_updated),
                },
                vector=paper.embedding,
            )
            points.append(point)

        try:
            self.logger.info(f"Inserting batch of {len(points)} papers into collection")
            await self.client.upsert(
                collection_name=self.collection_name, points=points
            )
            self.logger.info(f"Successfully inserted {len(points)} papers")
            return True
        except Exception as e:
            self.logger.error(f"Error inserting batch: {str(e)}")
            return False

    async def search_by_id(self, paper_id: str) -> Optional[SearchResult]:
        if not self.is_server_running():
            self.logger.error(
                f"Cannot search for ID {paper_id}: Qdrant server is not running"
            )
            return None

        try:
            id_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="id", match=models.MatchValue(value=paper_id)
                    )
                ]
            )

            results = await self.client.scroll(
                collection_name=self.collection_name,
                limit=1,
                scroll_filter=id_filter,
            )

            if results and results[0]:
                point = results[0][0]
                return SearchResult(
                    distance=0.0,
                    metadata=PaperMetadata(
                        paper_id=point.payload.get("id"),
                        categories=point.payload.get("categories"),
                        date_updated=unix_to_iso(point.payload.get("date_updated")),
                    ),
                )
            else:
                self.logger.warning(f"Paper with ID {paper_id} not found")
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving paper by ID: {str(e)}")
            return None

    async def search_by_query(
        self,
        query: Optional[str] = None,
        categories: Optional[List[ArxivDomains]] = None,
        categories_match_all: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        if not self.is_server_running():
            self.logger.error(
                "Cannot perform search query: Qdrant server is not running"
            )
            return []

        try:
            filter_conditions = []

            if categories:
                category_values = [
                    cat.value if isinstance(cat, ArxivDomains) else cat
                    for cat in categories
                ]

                if categories_match_all:
                    for category in category_values:
                        filter_conditions.append(
                            models.FieldCondition(
                                key="categories",
                                match=models.MatchValue(value=category),
                            )
                        )
                else:
                    filter_conditions.append(
                        models.FieldCondition(
                            key="categories", match=models.MatchAny(any=category_values)
                        )
                    )

            if date_from:
                filter_conditions.append(
                    models.FieldCondition(
                        key="date_updated",
                        range=models.Range(gte=iso_date_to_unix(date_from)),
                    )
                )

            if date_to:
                filter_conditions.append(
                    models.FieldCondition(
                        key="date_updated",
                        range=models.Range(lte=iso_date_to_unix(date_to)),
                    )
                )

            search_filter = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            if not query:
                results, next_page = await self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    scroll_filter=search_filter,
                )

                search_results = [
                    SearchResult(
                        distance=0.0,
                        metadata=PaperMetadata(
                            paper_id=point.payload.get("id"),
                            categories=point.payload.get("categories"),
                            date_updated=unix_to_iso(point.payload.get("date_updated")),
                        ),
                    )
                    for point in results
                ]
            else:
                query_vector = await self.embedder.embed_query(query)
                if not query_vector:
                    self.logger.error("Failed to generate embedding for search query")
                    return []

                results = await self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=search_filter,
                )

                search_results = [
                    SearchResult(
                        distance=1.0 - point.score,
                        metadata=PaperMetadata(
                            paper_id=point.payload.get("id"),
                            categories=point.payload.get("categories"),
                            date_updated=unix_to_iso(point.payload.get("date_updated")),
                        ),
                    )
                    for point in results
                ]

            return search_results

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []
