import asyncio
import logging.config
import time

from config import LOG_CONFIG
from process.database import Database
from process.read import Parser
from process.embed import Embedder

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)


# 2545 seconds for 1 Lakh Papers


class Pipeline:
    def __init__(self):
        self.parser = Parser()
        self.database = Database()
        self.embedder = Embedder()
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
        papers_per_sec = self.stats["papers_processed"] / elapsed if elapsed > 0 else 0
        logger.info(
            f"Progress: {self.stats['batches_processed']} batches | "
            f"{self.stats['papers_processed']} papers processed | "
            f"{self.stats['papers_embedded']} embedded | "
            f"{self.stats['papers_stored']} stored | "
            f"{self.stats['errors']} errors | "
            f"Rate: {papers_per_sec:.2f} papers/sec"
        )

    async def run(self):
        logger.info("Starting pipeline...")

        # Ensure database is ready
        db_ready = await self.database.create_collection_if_not_exists()
        if not db_ready:
            logger.error(
                "Database collection could not be created or accessed. Aborting pipeline."
            )
            return

        try:
            async for batch in self.parser.parse_yield_batches():
                batch_size = len(batch)
                self.stats["papers_processed"] += batch_size
                self.stats["batches_processed"] += 1

                if batch:
                    try:
                        try:
                            embedded_papers = await asyncio.wait_for(
                                self.embedder.embed_batch(batch),
                                timeout=300,
                            )
                            self.stats["papers_embedded"] += len(embedded_papers)

                            if embedded_papers:
                                insert_success = await self.database.insert_batch(
                                    embedded_papers
                                )
                                if insert_success:
                                    self.stats["papers_stored"] += len(embedded_papers)
                                else:
                                    logger.warning(
                                        f"Failed to insert batch of {len(embedded_papers)} papers"
                                    )
                        except asyncio.TimeoutError:
                            self.stats["errors"] += 1
                            logger.error(
                                f"Timeout while processing batch of {batch_size} papers"
                            )
                    except Exception as e:
                        self.stats["errors"] += 1
                        logger.error(f"Error processing batch: {str(e)}")

                self.log_progress()

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            self.stats["errors"] += 1

        elapsed = time.time() - self.stats["start_time"]
        logger.info(f"Pipeline completed in {elapsed:.2f} seconds")
        logger.info(f"Processed {self.stats['papers_processed']} papers")
        logger.info(f"Embedded {self.stats['papers_embedded']} papers")
        logger.info(f"Stored {self.stats['papers_stored']} papers")
        logger.info(f"Encountered {self.stats['errors']} errors")


async def main():
    pipeline = Pipeline()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
