import orjson
import aiofiles
import logging.config
from typing import AsyncIterator, List
from pydantic import ValidationError

from models import PaperMetadata
from config import (
    LOG_CONFIG,
    ARXIV_JSON_METADATASET_FILE,
    BATCH_SIZE,
    LAST_PAPER_PROCESSED_FILE,
    IF_OLD_PAPERS_PROCESSED_FILE,
)

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.json_file = ARXIV_JSON_METADATASET_FILE
        self.batch_size = BATCH_SIZE
        self.logger = logging.getLogger(__name__)
        self.last_id_processed = None
        self.if_old_papers_processed = None

    def id_to_int(self, id_str: str) -> int:
        try:
            parts = id_str.split(".")
            if len(parts) == 2:
                return int(parts[0]) * 10000 + int(parts[1])
            else:
                return -1
        except Exception:
            return -1

    def is_new_id(self, id: str):
        if "/" in id:
            return False
        elif "." in id:
            return True

    async def load_if_old_papers_processed(self):
        try:
            async with aiofiles.open(IF_OLD_PAPERS_PROCESSED_FILE, "r") as file:
                content = (await file.read()).strip().lower()
                if content:
                    value = content in ["true"]
                    self.logger.info(f"Are Old-form IDs already processed? {value}")
                    self.if_old_papers_processed = value
                else:
                    self.logger.info("No flag file found, starting fresh")
                    self.if_old_papers_processed = False
        except FileNotFoundError:
            self.logger.warning(
                f"File {IF_OLD_PAPERS_PROCESSED_FILE} not found, starting fresh."
            )
            self.if_old_papers_processed = False
        except Exception as e:
            self.logger.error(f"Error loading if old papers are processed: {e}")

    async def save_if_old_papers_processed(self, value: bool):
        try:
            async with aiofiles.open(IF_OLD_PAPERS_PROCESSED_FILE, "w") as file:
                await file.write("true" if value else "false")
                self.logger.info(f"Flag saved: Old-form IDs processed? {value}")
        except Exception as e:
            self.logger.error(f"Error saving flag for old-form papers: {e}")

    async def load_last_id(self):
        try:
            async with aiofiles.open(LAST_PAPER_PROCESSED_FILE, "r") as file:
                last_id = await file.read()
                if last_id:
                    self.logger.info(f"Last ID loaded: {last_id}")
                    self.last_id_processed = last_id
                else:
                    self.logger.info("No Last ID file found, starting fresh")
                    self.last_id_processed = "0704.0000"
        except FileNotFoundError:
            self.logger.warning(
                f"File {LAST_PAPER_PROCESSED_FILE} not found, starting fresh."
            )
            self.last_id_processed = ""
        except Exception as e:
            self.logger.error(f"Error loading last ID: {e}")

    async def save_last_id(self, id: str):
        try:
            async with aiofiles.open(LAST_PAPER_PROCESSED_FILE, "w") as file:
                await file.write(f"{id}")
                self.logger.info(f"Last ID saved: {id}")
        except Exception as e:
            self.logger.error(f"Error saving last ID: {e}")

    async def gen_batches(self) -> AsyncIterator[List[PaperMetadata]]:
        try:
            batch: List[PaperMetadata] = []

            async with aiofiles.open(self.json_file, mode="r") as f:
                async for line in f:
                    try:
                        data = orjson.loads(line)
                        id = data["id"]

                        if (
                            not (self.is_new_id(id)) and self.if_old_papers_processed
                        ):  # Assumes that new IDs are sequential, ascending and appended with each update to the snapshot.
                            continue

                        if self.last_id_processed and self.id_to_int(
                            id
                        ) < self.id_to_int(self.last_id_processed):
                            continue

                        entry = PaperMetadata(
                            id=data["id"],
                            abstract=data["abstract"],
                            title=data["title"],
                        )
                        batch.append(entry)

                        if len(batch) >= self.batch_size:
                            await self.save_last_id(batch[-1].id)
                            yield batch
                            batch = []
                    except ValidationError as e:
                        self.logger.warning(f"Validation error: {e}")
                        continue

            if batch:
                await self.save_last_id(batch[-1].id)
                await self.save_if_old_papers_processed(
                    True
                )  # because the first run of 2.7 million papers would cover all old-form IDs.
                yield batch
        except Exception as e:
            self.logger.error(f"Unexpected error during batch generation: {e}")
