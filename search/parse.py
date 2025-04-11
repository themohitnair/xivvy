import orjson
from models import PaperMetadata
import aiofiles
from pydantic import ValidationError
import logging.config

from config import LOG_CONFIG, ARXIV_JSON_METADATASET_FILE, BATCH_SIZE
from typing import AsyncIterator, List

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.json_file = ARXIV_JSON_METADATASET_FILE
        self.batch_size = BATCH_SIZE
        self.logger = logging.getLogger(__name__)

    async def gen_batches(self) -> AsyncIterator[List[PaperMetadata]]:
        try:
            batch: List[PaperMetadata] = []

            async with aiofiles.open(self.json_file, mode="r") as f:
                async for line in f:
                    try:
                        data = orjson.loads(line)

                        entry = PaperMetadata(
                            id=data["id"],
                            abstract=data["abstract"],
                            title=data["title"],
                        )
                        batch.append(entry)

                        if len(batch) >= self.batch_size:
                            yield batch
                            batch = []
                    except ValidationError as e:
                        self.logger.warning(f"Validation error: {e}")
                        continue

            if batch:
                yield batch
        except Exception as e:
            self.logger.error(f"Unexpected error during batch generation: {e}")
