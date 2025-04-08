import json
from typing import AsyncIterator, List
import os
from models import PaperMetadata
import aiofiles
from pydantic import ValidationError
import logging.config
from config import LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.json_file = os.path.join("data", "arxiv-metadata-oai-test.json")
        self.batch_size = 512
        self.logger = logging.getLogger(__name__)

    async def gen_batches(self) -> AsyncIterator[List[PaperMetadata]]:
        try:
            batch: List[PaperMetadata] = []

            async with aiofiles.open(self.json_file, mode="r") as f:
                async for line in f:
                    try:
                        data = json.loads(line)
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

            if batch:
                yield batch
        except Exception as e:
            self.logger.error(f"Unexpected error during batch generation: {e}")
