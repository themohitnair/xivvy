import logging.config
import asyncio
from typing import List
from light_embed import TextEmbedding
from cachetools import LRUCache

from models import ExtractedPaper, StoredPaper
from config import LOG_CONFIG, CACHE_SIZE, EMB_MODEL

logging.config.dictConfig(LOG_CONFIG)


class Embedder:
    def __init__(self):
        # Initialize light_embed client
        self.embedder = TextEmbedding(EMB_MODEL)
        self.logger = logging.getLogger(__name__)
        # Cache for query embeddings
        self.query_cache = LRUCache(maxsize=CACHE_SIZE)
        # Semaphore to limit concurrent processing
        self.semaphore = asyncio.Semaphore(5)

    async def embed_query(self, query: str) -> List[float] | None:
        if not query or not query.strip():
            self.logger.warning("Cannot embed empty query")
            return None

        # Truncate extremely long queries
        if len(query) > 1000:
            self.logger.warning(
                f"Query too long ({len(query)} chars), truncating to 1000 chars"
            )
            query = query[:1000]

        # Check cache first
        try:
            if query in self.query_cache:
                self.logger.info("Cache hit for query embedding")
                return self.query_cache[query]
        except Exception as e:
            self.logger.warning(f"Error checking query cache: {e}")
            # Continue with embedding even if cache check fails

        try:
            async with self.semaphore:
                # Convert to async operation using run_in_executor
                loop = asyncio.get_event_loop()
                try:
                    # Use run_in_executor to run the synchronous embedding in a thread pool
                    embedding_future = loop.run_in_executor(
                        None,  # Use default executor
                        lambda: self.embedder.encode([query])[0],
                    )

                    # Add timeout
                    embedding = await asyncio.wait_for(embedding_future, timeout=10.0)

                    # Validate embedding
                    if embedding is None or len(embedding) == 0:
                        self.logger.error("Empty embedding vector received")
                        return None

                    # Cache the result
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

    async def _process_sub_batch(
        self, sub_batch: List[ExtractedPaper]
    ) -> List[StoredPaper]:
        """Process a sub-batch of papers to avoid rate limits"""
        if not sub_batch:
            return []

        try:
            # Prepare inputs, filtering out any problematic texts
            valid_papers = []

            for paper in sub_batch:
                if not paper.abstract_title or len(paper.abstract_title.strip()) == 0:
                    self.logger.warning(
                        f"Skipping paper {paper.id} with empty abstract_title"
                    )
                    continue

                # Truncate extremely long texts
                if len(paper.abstract_title) > 1500:
                    paper.abstract_title = paper.abstract_title[:1500]
                    self.logger.warning(f"Truncated long abstract for paper {paper.id}")

                valid_papers.append(paper)

            if not valid_papers:
                self.logger.warning("No valid papers to embed in sub-batch")
                return []

            async with self.semaphore:
                loop = asyncio.get_event_loop()
                papers_to_store = []

                # Process each paper individually to handle errors better
                for paper in valid_papers:
                    try:
                        # Use run_in_executor to run the synchronous embedding in a thread pool
                        embedding_future = loop.run_in_executor(
                            None,  # Use default executor
                            lambda p=paper: self.embedder.encode([p.abstract_title])[0],
                        )

                        # Add timeout
                        embedding = await asyncio.wait_for(
                            embedding_future, timeout=10.0
                        )

                        if embedding is None or len(embedding) == 0:
                            self.logger.warning(
                                f"Empty embedding for paper {paper.id}, skipping"
                            )
                            continue

                        papers_to_store.append(
                            StoredPaper(
                                paper_id=paper.id,
                                embedding=embedding,
                                categories=paper.categories,
                                date_updated=paper.date_updated,
                            )
                        )
                    except Exception as item_error:
                        self.logger.error(
                            f"Error processing paper {paper.id}: {item_error}"
                        )
                        continue

                self.logger.info(
                    f"Successfully embedded {len(papers_to_store)} out of {len(valid_papers)} papers"
                )
                return papers_to_store
        except Exception as e:
            self.logger.error(f"Error embedding sub-batch: {e}")
            return []

    async def embed_batch(self, batch: List[ExtractedPaper]) -> List[StoredPaper]:
        if not batch:
            self.logger.warning("Received empty batch for embedding")
            return []

        try:
            # Validate batch items
            valid_batch = []
            for paper in batch:
                if not paper.id:
                    self.logger.warning("Skipping paper with missing ID")
                    continue
                if not paper.abstract_title:
                    self.logger.warning(
                        f"Skipping paper {paper.id} with missing abstract_title"
                    )
                    continue
                valid_batch.append(paper)

            if not valid_batch:
                self.logger.warning("No valid papers in batch after validation")
                return []

            # Split into smaller sub-batches to avoid rate limits and timeout issues
            sub_batch_size = 50  # Smaller batches to avoid timeouts
            sub_batches = [
                valid_batch[i : i + sub_batch_size]
                for i in range(0, len(valid_batch), sub_batch_size)
            ]

            # Process sub-batches concurrently with error handling
            self.logger.info(f"Processing {len(sub_batches)} sub-batches of papers")
            tasks = [self._process_sub_batch(sub_batch) for sub_batch in sub_batches]

            try:
                # Use gather with return_exceptions to prevent one failed task from failing all
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results, handling any exceptions
                papers_to_store = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Sub-batch {i} failed: {str(result)}")
                    else:
                        papers_to_store.extend(result)

                success_rate = (
                    len(papers_to_store) / len(valid_batch) if valid_batch else 0
                )
                self.logger.info(
                    f"Embedded {len(papers_to_store)} out of {len(valid_batch)} papers "
                    f"({success_rate:.1%} success rate)"
                )
                return papers_to_store
            except Exception as gather_error:
                self.logger.error(f"Error gathering embedding results: {gather_error}")
                # Try to salvage any results we can by processing tasks individually
                papers_to_store = []
                for i, task in enumerate(tasks):
                    try:
                        if task.done() and not task.exception():
                            papers_to_store.extend(task.result())
                    except Exception:
                        pass  # Already logged in _process_sub_batch

                self.logger.info(f"Salvaged {len(papers_to_store)} papers after error")
                return papers_to_store
        except Exception as e:
            self.logger.error(f"Error in batch embedding process: {e}")
            return []
