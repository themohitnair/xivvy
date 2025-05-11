import logging.config
import socket
import asyncio
from qdrant_client import AsyncQdrantClient, models
from typing import List, Optional
from cachetools import TTLCache

from config import (
    DB_COLLECTION_NAME,
    DB_PORT,
    LOG_CONFIG,
    CACHE_SIZE,
    CACHE_TTL,
    VECTOR_SIZE,
)
from models import ArxivDomains, StoredPaper, SearchResult, PaperMetadata
from process.embed import Embedder
from utils import string_to_uuid, iso_date_to_unix, unix_to_iso

logging.config.dictConfig(LOG_CONFIG)


class Database:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.client = AsyncQdrantClient(
            url=f"http://qdrant:{DB_PORT}",
            prefer_grpc=True,
            timeout=10.0,
        )
        self.logger.info("Connected to port 6333 (Qdrant Database).")
        self.collection_name = DB_COLLECTION_NAME
        self.embedder = Embedder()

        self.id_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
        self.query_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)

        self.semaphore = asyncio.Semaphore(20)

    def is_server_running(self) -> bool:
        host = "qdrant"
        port = DB_PORT

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                try:
                    sock.connect((host, port))
                    self.logger.info(f"Qdrant server is running on {host}:{port}")
                    return True
                except (ConnectionRefusedError, socket.timeout):
                    self.logger.warning(
                        f"Qdrant server not accessible at {host}:{port}"
                    )
                    return False
        except Exception as e:
            self.logger.error(f"Unexpected error checking server status: {str(e)}")
            return False

    async def create_collection_if_not_exists(self) -> bool:
        if not self.is_server_running():
            self.logger.error("Cannot create collection: Qdrant server is not running")
            return False

        try:
            collection_exists = await asyncio.wait_for(
                self.client.collection_exists(self.collection_name), timeout=5.0
            )

            if collection_exists:
                self.logger.info(f"Collection '{self.collection_name}' found.")
                return True
            else:
                self.logger.info(
                    f"Collection '{self.collection_name}' not found. Creating..."
                )
                try:
                    await self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=VECTOR_SIZE,
                            distance=models.Distance.COSINE,
                            on_disk=True,
                        ),
                        quantization_config=models.ScalarQuantization(
                            scalar=models.ScalarQuantizationConfig(
                                type=models.ScalarType.INT8,
                                always_ram=True,
                            ),
                        ),
                    )
                    self.logger.info(f"Created collection '{self.collection_name}'.")
                    return True
                except asyncio.TimeoutError:
                    self.logger.error("Timeout while creating collection")
                    return False
        except asyncio.TimeoutError:
            self.logger.error("Timeout while checking if collection exists")
            return False
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

        points = [
            models.PointStruct(
                id=str(string_to_uuid(paper.paper_id)),
                payload={
                    "id": paper.paper_id,
                    "categories": [cat.value for cat in paper.categories],
                    "authors": paper.authors,
                    "title": paper.title,
                    "date_updated": iso_date_to_unix(paper.date_updated),
                },
                vector=paper.embedding,
            )
            for paper in batch
        ]

        try:
            async with self.semaphore:
                self.logger.info(
                    f"Inserting batch of {len(points)} papers into collection"
                )
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,
                )

                self.id_cache.clear()
                self.query_cache.clear()

                self.logger.info(f"Successfully inserted {len(points)} papers")
                return True
        except Exception as e:
            self.logger.error(f"Error inserting batch: {str(e)}")
            return False

    async def search_by_id(self, paper_id: str) -> Optional[SearchResult]:
        if not paper_id:
            self.logger.error("Cannot search with empty paper_id")
            return None

        if paper_id in self.id_cache:
            self.logger.info(f"Cache hit for paper ID: {paper_id}")
            return self.id_cache[paper_id]

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

            try:
                async with self.semaphore:
                    results = await asyncio.wait_for(
                        self.client.scroll(
                            collection_name=self.collection_name,
                            limit=1,
                            scroll_filter=id_filter,
                            with_payload=True,
                            with_vectors=False,
                        ),
                        timeout=5.0,
                    )

                if results and results[0]:
                    point = results[0][0]
                    if not point.payload or not all(
                        k in point.payload for k in ["id", "categories", "date_updated"]
                    ):
                        self.logger.warning(
                            f"Incomplete payload for paper ID {paper_id}"
                        )
                        return None

                    try:
                        paper_id = point.payload.get("id")
                        categories = point.payload.get("categories", [])
                        date_updated = unix_to_iso(point.payload.get("date_updated"))

                        authors = point.payload.get("authors", ["Unknown"])
                        if not isinstance(authors, list):
                            try:
                                if isinstance(authors, str):
                                    authors = [
                                        a.strip()
                                        for a in authors.split(",")
                                        if a.strip()
                                    ]
                                else:
                                    authors = [str(authors)]
                            except Exception:
                                authors = ["Unknown"]
                        if not authors:
                            authors = ["Unknown"]

                        title = point.payload.get("title")
                        if not title or not isinstance(title, str) or not title.strip():
                            title = f"Paper {paper_id}"
                        else:
                            title = " ".join(title.split())

                        result = SearchResult(
                            distance=None,
                            metadata=PaperMetadata(
                                paper_id=paper_id,
                                categories=categories,
                                authors=authors,
                                title=title,
                                date_updated=date_updated,
                            ),
                        )
                        self.id_cache[paper_id] = result
                        return result
                    except Exception as e:
                        self.logger.error(f"Error creating SearchResult: {str(e)}")
                        return None
                else:
                    self.logger.warning(f"Paper with ID {paper_id} not found")
                    return None
            except asyncio.TimeoutError:
                self.logger.error(f"Timeout while searching for paper ID {paper_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving paper by ID: {str(e)}")
            return None

    def _create_cache_key(
        self,
        query: Optional[str],
        categories: Optional[List[ArxivDomains]],
        categories_match_all: bool,
        date_from: Optional[str],
        date_to: Optional[str],
        limit: int,
    ) -> str:
        """Create a cache key from search parameters"""
        cat_str = ",".join(
            sorted(
                [
                    c.value if isinstance(c, ArxivDomains) else c
                    for c in (categories or [])
                ]
            )
        )
        return f"{query}:{cat_str}:{categories_match_all}:{date_from}:{date_to}:{limit}"

    async def search_by_query(
        self,
        query: Optional[str] = None,
        categories: Optional[List[ArxivDomains]] = None,
        categories_match_all: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        if limit <= 0:
            self.logger.warning(f"Invalid limit value: {limit}, using default of 10")
            limit = 10
        elif limit > 100:
            self.logger.warning(f"Limit too large: {limit}, capping at 100")
            limit = 100

        try:
            cache_key = self._create_cache_key(
                query, categories, categories_match_all, date_from, date_to, limit
            )
            if cache_key in self.query_cache:
                self.logger.info("Cache hit for query search")
                return self.query_cache[cache_key]
        except Exception as e:
            self.logger.error(f"Error creating cache key: {str(e)}")

        if not self.is_server_running():
            self.logger.error(
                "Cannot perform search query: Qdrant server is not running"
            )
            return []

        try:
            filter_conditions = []

            if categories:
                try:
                    category_values = [
                        cat.value if isinstance(cat, ArxivDomains) else cat
                        for cat in categories
                        if cat is not None
                    ]

                    if category_values:
                        if categories_match_all:
                            for cat_value in category_values:
                                filter_conditions.append(
                                    models.FieldCondition(
                                        key="categories",
                                        match=models.MatchValue(value=cat_value),
                                    )
                                )
                        else:
                            filter_conditions.append(
                                models.FieldCondition(
                                    key="categories",
                                    match=models.MatchAny(any=category_values),
                                )
                            )
                except Exception as e:
                    self.logger.error(f"Error processing categories: {str(e)}")

            try:
                date_range_params = {}
                if date_from:
                    date_range_params["gte"] = iso_date_to_unix(date_from)
                if date_to:
                    date_range_params["lte"] = iso_date_to_unix(date_to)

                if date_range_params:
                    filter_conditions.append(
                        models.FieldCondition(
                            key="date_updated",
                            range=models.Range(**date_range_params),
                        )
                    )
            except Exception as e:
                self.logger.error(f"Error processing date filters: {str(e)}")

            search_filter = (
                models.Filter(must=filter_conditions) if filter_conditions else None
            )

            async with self.semaphore:
                if not query:
                    scroll_response = await self.client.scroll(
                        collection_name=self.collection_name,
                        limit=limit,
                        scroll_filter=search_filter,
                        with_payload=True,
                        with_vectors=False,
                    )

                    results = []
                    for point, _ in scroll_response[0]:
                        try:
                            if not point.payload or not all(
                                k in point.payload
                                for k in ["id", "categories", "date_updated"]
                            ):
                                self.logger.warning(
                                    f"Incomplete payload for paper ID {point.payload.get('id', 'unknown')}"
                                )
                                continue

                            paper_id = point.payload.get("id")
                            categories = point.payload.get("categories", [])
                            date_updated = unix_to_iso(
                                point.payload.get("date_updated")
                            )

                            authors = point.payload.get("authors", ["Unknown"])
                            title = point.payload.get("title", f"Paper {paper_id}")

                            results.append(
                                SearchResult(
                                    distance=None,
                                    metadata=PaperMetadata(
                                        paper_id=paper_id,
                                        categories=categories,
                                        authors=authors,
                                        title=title,
                                        date_updated=date_updated,
                                    ),
                                )
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error processing search result: {str(e)}"
                            )
                else:
                    query_vector = await self.embedder.embed_query(query)
                    if query_vector is None or getattr(query_vector, "size", 0) == 0:
                        self.logger.error(
                            "Failed to generate embedding for search query"
                        )
                        return []

                    search_results = await self.client.search(
                        collection_name=self.collection_name,
                        query_vector=query_vector,
                        limit=limit,
                        query_filter=search_filter,
                        with_payload=True,
                    )

                    results = []
                    for point in search_results:
                        try:
                            if not point.payload or not all(
                                k in point.payload
                                for k in ["id", "categories", "date_updated"]
                            ):
                                self.logger.warning(
                                    f"Incomplete payload for paper ID {point.payload.get('id', 'unknown')}"
                                )
                                continue

                            paper_id = point.payload.get("id")
                            categories = point.payload.get("categories", [])
                            date_updated = unix_to_iso(
                                point.payload.get("date_updated")
                            )

                            authors = point.payload.get("authors", ["Unknown"])
                            title = point.payload.get("title", f"Paper {paper_id}")

                            results.append(
                                SearchResult(
                                    distance=1.0 - point.score,
                                    metadata=PaperMetadata(
                                        paper_id=paper_id,
                                        categories=categories,
                                        authors=authors,
                                        title=title,
                                        date_updated=date_updated,
                                    ),
                                )
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error processing search result: {str(e)}"
                            )
                            continue

                    search_results = results

            self.query_cache[cache_key] = search_results
            return search_results

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []
