import logging.config
import asyncio
from typing import List
from light_embed import TextEmbedding
from cachetools import LRUCache

from config import LOG_CONFIG, CACHE_SIZE, EMB_MODEL

logging.config.dictConfig(LOG_CONFIG)


class Embedder:
    def __init__(self):
        self.embedder = TextEmbedding(EMB_MODEL)
        self.logger = logging.getLogger(__name__)
        self.query_cache = LRUCache(maxsize=CACHE_SIZE)
        self.semaphore = asyncio.Semaphore(5)

    async def embed_query(self, query: str) -> List[float] | None:
        if not query or not query.strip():
            self.logger.warning("Cannot embed empty query")
            return None

        if len(query) > 1000:
            self.logger.warning(
                f"Query too long ({len(query)} chars), truncating to 1000 chars"
            )
            query = query[:1000]

        try:
            if query in self.query_cache:
                self.logger.info("Cache hit for query embedding")
                return self.query_cache[query]
        except Exception as e:
            self.logger.warning(f"Error checking query cache: {e}")

        try:
            async with self.semaphore:
                loop = asyncio.get_event_loop()
                try:
                    embedding_future = loop.run_in_executor(
                        None,
                        lambda: self.embedder.encode([query])[0],
                    )

                    embedding = await asyncio.wait_for(embedding_future, timeout=10.0)

                    if embedding is None or len(embedding) == 0:
                        self.logger.error("Empty embedding vector received")
                        return None

                    try:
                        self.query_cache[query] = embedding
                    except Exception as cache_error:
                        self.logger.warning(f"Failed to cache embedding: {cache_error}")

                    self.logger.info(
                        f"Successfully embedded query ({len(embedding)} dimensions)"
                    )
                    return embedding
                except asyncio.TimeoutError:
                    self.logger.error("Timeout while embedding query")
                    return None
        except Exception as e:
            self.logger.error(f"Error embedding query: {e}")
            return None
