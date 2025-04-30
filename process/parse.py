from typing import List, AsyncIterator
import aiofiles
import orjson
import logging.config
from config import LOG_CONFIG, DATASET_PATH, BATCH_SIZE, VALID_CATEGORIES
from models import PaperExtracted

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.file_path = DATASET_PATH
        self.logger = logging.getLogger(__name__)
        self.batch_size = BATCH_SIZE
        self.valid_categories = VALID_CATEGORIES

    def normalize_category(self, category: str) -> str:
        if category in self.valid_categories:
            return category

        for valid_cat in self.valid_categories:
            if category.startswith(valid_cat + ".") or category.startswith(
                valid_cat + "-"
            ):
                return valid_cat

        return category

    async def parse_yield_batches(self) -> AsyncIterator[List[PaperExtracted]]:
        batch = []
        async with aiofiles.open(self.file_path) as f:
            async for line in f:
                if not line.strip():
                    continue

                try:
                    obj = orjson.loads(line)

                    paper_id = obj.get("id", "").strip()
                    title = (obj.get("title") or "").strip()
                    abstract = (obj.get("abstract") or "").strip()
                    categories_raw = obj.get("categories", "").strip()
                    update_date = obj.get("update_date", "").strip()

                    if not paper_id or not (title or abstract):
                        self.logger.warning(
                            f"Skipping paper due to missing id/title/abstract: {obj['id']}"
                        )
                        continue
                    categories = []
                    if categories_raw:
                        categories = sorted(
                            {
                                self.normalize_category(cat.strip())
                                for cat in categories_raw.split()
                                if cat
                            }
                        )

                    paper = PaperExtracted(
                        id=paper_id,
                        abstract_title=f"{title}\n\n{abstract}",
                        categories=categories,
                        date_published=update_date,
                    )

                except (orjson.JSONDecodeError, KeyError, AttributeError) as e:
                    self.logger.error(f"Malformed JSON found: {e} - Line: {line}")
                    continue
                except Exception as e:
                    self.logger.error(f"Unexpected parsing error: {e} — Line: {line}")
                    continue

                batch.append(paper)

                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []

            if batch:
                yield batch
