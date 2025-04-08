import asyncio
import gc
import logging.config

from config import LOG_CONFIG
from search.parse import Parser
from search.embed import Embedder
from search.database import Database


async def load_and_upsert() -> None:
    logging.config.dictConfig(LOG_CONFIG)
    logger = logging.getLogger("load_dataset")

    parser = Parser()
    embedder = Embedder()
    db = Database()

    logger.info("Initializing database…")
    await db.initialize()
    logger.info("✅ Database ready")

    batch_idx = 0
    total_papers = 0

    logger.info("Starting parsing → embedding → upsert pipeline")
    async for batch in parser.gen_batches():
        batch_idx += 1
        logger.info(f"🔄 Batch {batch_idx}: {len(batch)} papers")

        # embed
        entries = embedder.embed_batch(batch)
        logger.debug(f"   ↳ Embedded batch {batch_idx}")

        # upsert
        await db.upsert(entries)
        logger.info(f"✅ Upserted batch {batch_idx}")

        del entries
        gc.collect()

        total_papers += len(batch)

    logger.info(
        f"🎉 Pipeline complete: {batch_idx} batches, {total_papers} papers loaded"
    )


def main():
    asyncio.run(load_and_upsert())


if __name__ == "__main__":
    main()
