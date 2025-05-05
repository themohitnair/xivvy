import logging.config
from typing import List
from together import AsyncTogether

from models import ExtractedPaper, StoredPaper
from config import TGA_KEY, EMB_MODEL, LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)


class Embedder:
    def __init__(self):
        self.client = AsyncTogether(api_key=TGA_KEY)
        self.model = EMB_MODEL
        self.logger = logging.getLogger(__name__)

    async def embed_query(self, query: str) -> List[float] | None:
        try:
            response = await self.client.embeddings.create(
                input=[query], model=self.model
            )

            self.logger.info("Successfully embedded the query.")
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error embedding batch: {e}")
            return None

    async def embed_batch(self, batch: List[ExtractedPaper]) -> List[StoredPaper]:
        try:
            response = await self.client.embeddings.create(
                input=[paper.abstract_title for paper in batch], model=self.model
            )

            papers_to_store = []

            for i, paper in enumerate(batch):
                embedding = response.data[i].embedding
                papers_to_store.append(
                    StoredPaper(
                        paper_id=paper.id,
                        embedding=embedding,
                        categories=paper.categories,
                        date_updated=paper.date_updated,
                    )
                )

            self.logger.info(f"Successfully embedded batch of {len(batch)} papers.")
            return papers_to_store
        except Exception as e:
            self.logger.error(f"Error embedding batch: {e}")
            return []
