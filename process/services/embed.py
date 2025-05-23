import logging.config
import asyncio
from typing import List
from light_embed import TextEmbedding

from models import ExtractedPaper, StoredPaper
from config import LOG_CONFIG, EMB_MODEL

logging.config.dictConfig(LOG_CONFIG)


class Embedder:
    def __init__(self):
        self.embedder = TextEmbedding(EMB_MODEL)
        self.logger = logging.getLogger(__name__)
        self.semaphore = asyncio.Semaphore(5)

    async def _process_sub_batch(
        self, sub_batch: List[ExtractedPaper]
    ) -> List[StoredPaper]:
        """Process a sub-batch of papers to avoid rate limits"""
        if not sub_batch:
            return []

        try:
            valid_papers = []
            paper_texts = []

            for paper in sub_batch:
                combined_text = f"{paper.title} {paper.abstract}".strip()

                if not combined_text:
                    self.logger.warning(
                        f"Skipping paper {paper.id} with empty title and abstract"
                    )
                    continue

                if len(combined_text) > 1500:
                    combined_text = combined_text[:1500]
                    self.logger.warning(f"Truncated long text for paper {paper.id}")

                valid_papers.append(paper)
                paper_texts.append(combined_text)

            if not valid_papers:
                self.logger.warning("No valid papers to embed in sub-batch")
                return []

            async with self.semaphore:
                loop = asyncio.get_event_loop()
                papers_to_store = []

                for i, paper in enumerate(valid_papers):
                    try:
                        combined_text = paper_texts[i]

                        embedding_future = loop.run_in_executor(
                            None,  # Use default executor
                            lambda text=combined_text: self.embedder.encode([text])[0],
                        )

                        embedding = await asyncio.wait_for(
                            embedding_future, timeout=10.0
                        )

                        if embedding is None or len(embedding) == 0:
                            self.logger.warning(
                                f"Empty embedding for paper {paper.id}, skipping"
                            )
                            continue

                        papers_to_store.append(
                            StoredPaper(
                                paper_id=paper.id,
                                embedding=embedding,
                                categories=paper.categories,
                                authors=paper.authors,
                                title=paper.title,
                                date_updated=paper.date_updated,
                            )
                        )
                    except Exception as item_error:
                        self.logger.error(
                            f"Error processing paper {paper.id}: {item_error}"
                        )
                        continue

                self.logger.info(
                    f"Successfully embedded {len(papers_to_store)} out of {len(valid_papers)} papers"
                )
                return papers_to_store
        except Exception as e:
            self.logger.error(f"Error embedding sub-batch: {e}")
            return []

    async def embed_batch(self, batch: List[ExtractedPaper]) -> List[StoredPaper]:
        if not batch:
            self.logger.warning("Received empty batch for embedding")
            return []

        try:
            valid_batch = []
            for paper in batch:
                if not paper.id:
                    self.logger.warning("Skipping paper with missing ID")
                    continue
                if not (paper.title or paper.abstract):
                    self.logger.warning(
                        f"Skipping paper {paper.id} with missing both title and abstract"
                    )
                    continue
                valid_batch.append(paper)

            if not valid_batch:
                self.logger.warning("No valid papers in batch after validation")
                return []

            sub_batch_size = 50
            sub_batches = [
                valid_batch[i : i + sub_batch_size]
                for i in range(0, len(valid_batch), sub_batch_size)
            ]

            self.logger.info(f"Processing {len(sub_batches)} sub-batches of papers")
            tasks = [self._process_sub_batch(sub_batch) for sub_batch in sub_batches]

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                papers_to_store = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Sub-batch {i} failed: {str(result)}")
                    else:
                        papers_to_store.extend(result)

                success_rate = (
                    len(papers_to_store) / len(valid_batch) if valid_batch else 0
                )
                self.logger.info(
                    f"Embedded {len(papers_to_store)} out of {len(valid_batch)} papers "
                    f"({success_rate:.1%} success rate)"
                )
                return papers_to_store
            except Exception as gather_error:
                self.logger.error(f"Error gathering embedding results: {gather_error}")
                papers_to_store = []
                for i, task in enumerate(tasks):
                    try:
                        if task.done() and not task.exception():
                            papers_to_store.extend(task.result())
                    except Exception:
                        pass

                self.logger.info(f"Salvaged {len(papers_to_store)} papers after error")
                return papers_to_store
        except Exception as e:
            self.logger.error(f"Error in batch embedding process: {e}")
            return []
