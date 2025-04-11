import asyncio
import logging.config
import time
from datetime import datetime
from typing import Optional

from config import LOG_CONFIG
from search.parse import Parser
from search.embed import Embedder
from search.database import Database
from utils import save_last_updated


async def startup_loading() -> None:
    logging.config.dictConfig(LOG_CONFIG)
    logger = logging.getLogger(__name__)
    embedder = Embedder()
    parser = Parser()

    async with Database() as db:
        logger.info("🚀 Starting pipeline")
        start_loading = time.perf_counter()

        total_papers = 0
        batch_idx = 0
        next_batch_task: Optional[asyncio.Task] = None

        async for raw_batch in parser.gen_batches():
            batch_size = len(raw_batch)
            logger.info(f"Batch {batch_idx + 1}: Received {batch_size} items")

            if next_batch_task:
                try:
                    entries = await next_batch_task
                    logger.debug(f"Batch {batch_idx}: Embedding complete")

                    upsert_task = asyncio.create_task(db.upsert(entries))
                    next_batch_task = asyncio.create_task(
                        embedder.embed_batch(raw_batch)
                    )

                    await upsert_task
                    logger.info(f"Batch {batch_idx}: Upserted {len(entries)} entries")
                except Exception as e:
                    logger.exception(f"Error processing batch {batch_idx}: {e}")
                    break
            else:
                try:
                    next_batch_task = asyncio.create_task(
                        embedder.embed_batch(raw_batch)
                    )
                    batch_idx += 1
                    total_papers += batch_size
                    continue
                except Exception as e:
                    logger.exception(f"Error starting embedding task: {e}")
                    break

            batch_idx += 1
            total_papers += batch_size

            elapsed = time.perf_counter() - start_loading
            papers_sec = total_papers / elapsed
            logger.info(
                f"📦 Batch {batch_idx} processed | Total so far: {total_papers} papers | "
                f"⏱️ Speed: {papers_sec:.2f} papers/sec"
            )

        if next_batch_task:
            try:
                entries = await next_batch_task
                await db.upsert(entries)
                logger.info(f"Final upsert: {len(entries)} entries")
            except Exception as e:
                logger.exception(f"Error in final batch: {e}")

        logger.info("⚙️ Optimizing production indexes...")
        start_index = time.perf_counter()
        await db.enable_production_indexing()
        logger.info(
            f"✅ Index optimization complete in {time.perf_counter() - start_index:.2f}s"
        )
        count = await db.count_vectors()

        logger.info(f"{count} vectors are in the Database.")

    total_time = time.perf_counter() - start_loading
    logger.info(
        f"🏁 Pipeline finished\n"
        f"• 📄 Total papers: {total_papers}\n"
        f"• ⌛ Total time: {total_time:.2f}s\n"
        f"• ⚡ Avg throughput: {total_papers / total_time:.2f} papers/sec"
    )
    save_last_updated(datetime.now())


def main():
    asyncio.run(startup_loading())


if __name__ == "__main__":
    main()
