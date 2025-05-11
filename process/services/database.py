import logging.config
import socket
import asyncio
from qdrant_client import AsyncQdrantClient, models
from typing import List
from cachetools import TTLCache

from config import (
    DB_COLLECTION_NAME,
    DB_PORT,
    LOG_CONFIG,
    CACHE_SIZE,
    CACHE_TTL,
    VECTOR_SIZE,
    HOST,
)
from models import StoredPaper
from services.embed import Embedder
from services.utils import string_to_uuid, iso_date_to_unix

logging.config.dictConfig(LOG_CONFIG)


class Database:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.client = AsyncQdrantClient(
            url=f"http://{HOST}:{DB_PORT}",
            prefer_grpc=True,
            timeout=10.0,
        )
        self.collection_name = DB_COLLECTION_NAME
        self.embedder = Embedder()

        self.id_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)
        self.query_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)

        self.semaphore = asyncio.Semaphore(20)

    def is_server_running(self) -> bool:
        host = HOST
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

    async def count_points(self) -> int:
        """
        Counts the number of points (entries) in the Qdrant collection.

        Returns:
            int: Number of points in the collection. Returns -1 if error occurs.
        """
        if not self.is_server_running():
            self.logger.error("Cannot count points: Qdrant server is not running")
            return -1

        try:
            async with self.semaphore:
                collection_info = await self.client.get_collection(self.collection_name)
                point_count = collection_info.points_count
                self.logger.info(
                    f"Collection '{self.collection_name}' contains {point_count} points."
                )
                return point_count
        except Exception as e:
            self.logger.error(f"Error retrieving collection info: {str(e)}")
            return -1
