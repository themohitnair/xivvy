import asyncio
import logging.config
import time

from config import LOG_CONFIG
from services.database import Database
from services.parse import Parser
from services.embed import Embedder

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, shutdown_event: asyncio.Event):
        self.parser = Parser()
        self.database = Database()
        self.embedder = Embedder()
        self.shutdown_event = shutdown_event
        self.stats = {
            "papers_processed": 0,
            "papers_embedded": 0,
            "papers_stored": 0,
            "batches_processed": 0,
            "errors": 0,
            "start_time": time.time(),
        }

    def log_progress(self):
        elapsed = time.time() - self.stats["start_time"]
        rate = self.stats["papers_processed"] / elapsed if elapsed > 0 else 0
        logger.info(
            f"Progress: {self.stats['batches_processed']} batches | "
            f"{self.stats['papers_processed']} papers processed | "
            f"{self.stats['papers_embedded']} embedded | "
            f"{self.stats['papers_stored']} stored | "
            f"{self.stats['errors']} errors | "
            f"Rate: {rate:.2f} papers/sec"
        )

    async def run(self):
        logger.info("Starting pipeline...")
        if not await self.database.create_collection_if_not_exists():
            logger.error("Cannot access DB collection; aborting.")
            return

        try:
            async for batch in self.parser.parse_yield_batches():
                if self.shutdown_event.is_set():
                    logger.info("Shutdown requested; exiting batch loop.")
                    break

                self.stats["batches_processed"] += 1
                self.stats["papers_processed"] += len(batch)

                try:
                    embedded = await asyncio.wait_for(
                        self.embedder.embed_batch(batch),
                        timeout=300,
                    )
                    self.stats["papers_embedded"] += len(embedded)

                    if await self.database.insert_batch(embedded):
                        self.stats["papers_stored"] += len(embedded)
                    else:
                        logger.warning(f"Insert failed for {len(embedded)} papers")

                except asyncio.TimeoutError:
                    self.stats["errors"] += 1
                    logger.error(f"Timeout embedding batch of size {len(batch)}")

                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"Error in batch: {e}")

                self.log_progress()

        finally:
            elapsed = time.time() - self.stats["start_time"]
            logger.info(f"Pipeline ended in {elapsed:.2f}s")
            logger.info(f"Papers processed: {self.stats['papers_processed']}")
            logger.info(f"Papers embedded: {self.stats['papers_embedded']}")
            logger.info(f"Papers stored: {self.stats['papers_stored']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info(f"Number of points: {await self.database.count_points()}")
