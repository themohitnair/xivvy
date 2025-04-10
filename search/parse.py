import json
from typing import AsyncIterator, List, Optional
from models import PaperMetadata
import aiofiles
from pydantic import ValidationError
import logging.config
from datetime import datetime
from config import LOG_CONFIG, ARXIV_JSON_METADATASET_FILE, BATCH_SIZE

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.json_file = ARXIV_JSON_METADATASET_FILE
        self.batch_size = BATCH_SIZE
        self.logger = logging.getLogger(__name__)

    async def gen_batches(
        self, date: Optional[datetime] = None
    ) -> AsyncIterator[List[PaperMetadata]]:
        try:
            batch: List[PaperMetadata] = []

            async with aiofiles.open(self.json_file, mode="r") as f:
                async for line in f:
                    try:
                        data = json.loads(line)

                        if date:
                            updated_at = data["update_date"]
                            if not updated_at:
                                continue
                            update_date = datetime.strptime(updated_at, "%Y-%m-%d")
                            if update_date <= date:
                                continue

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
