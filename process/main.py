import asyncio
import signal
import logging

from services.dataset import DatasetDownloader
from services.pipeline import Pipeline

logger = logging.getLogger(__name__)


def setup_signal_handlers(shutdown_event: asyncio.Event):
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)


async def main():
    downloader = DatasetDownloader()
    downloader.run()

    shutdown_event = asyncio.Event()
    setup_signal_handlers(shutdown_event)

    pipeline = Pipeline(shutdown_event)
    await pipeline.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user; exiting with stats above.")
