import re
import os
import json
import aiofiles
import orjson
import logging.config
import asyncio
from functools import lru_cache
from typing import List, AsyncIterator, Dict, Optional

from models import ExtractedPaper
from config import LOG_CONFIG, DATASET_PATH, BATCH_SIZE, VALID_CATEGORIES

logging.config.dictConfig(LOG_CONFIG)


class Parser:
    def __init__(self):
        self.file_path = DATASET_PATH
        self.logger = logging.getLogger(__name__)
        self.batch_size = BATCH_SIZE
        self.valid_categories = VALID_CATEGORIES

        # Legacy category mapping
        self.legacy_to_current_mapping = {
            "acc-phys": "physics",
            "adap-org": "nlin",
            "alg-geom": "math",
            "ao-sci": "physics",
            "atom-ph": "physics",
            "bayes-an": "stat",
            "chao-dyn": "nlin",
            "chem-ph": "physics",
            "cmp-lg": "cs",
            "comp-gas": "physics",
            "dg-ga": "math",
            "funct-an": "math",
            "mtrl-th": "cond-mat",
            "patt-sol": "nlin",
            "plasm-ph": "physics",
            "q-alg": "quant-ph",
            "solv-int": "nlin",
            "supr-con": "cond-mat",
        }

        self.checkpoint_file = "checkpoint.json"
        self.last_processed_id = self._load_checkpoint()
        self.logger.info(
            f"Starting from checkpoint ID: {self.last_processed_id or 'Beginning'}"
        )

        self.latex_patterns = {
            "math_inline": re.compile(r"\$.*?\$"),
            "math_inline2": re.compile(r"\\\((.*?)\\\)"),
            "math_block": re.compile(r"\\\[(.*?)\\\]"),
            "cite": re.compile(r"\\cite\{.*?\}"),
            "references": re.compile(
                r"(Figure|Fig\.|Eq\.|Equation|Section|Table)\s+\d+(\.\d+)?",
                re.IGNORECASE,
            ),
            "references2": re.compile(
                r"(Eq\.|Equation|Fig\.|Figure|Table|Section)\s*\(\d+\)", re.IGNORECASE
            ),
            "latex_commands": re.compile(r"\\[a-zA-Z]+"),
        }

        self.category_cache: Dict[str, str] = {}

    def _load_checkpoint(self) -> Optional[str]:
        """Load the last processed paper ID from checkpoint file"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r") as f:
                    checkpoint_data = json.load(f)
                    return checkpoint_data.get("last_processed_id")
            return None
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}")
            return None

    async def save_checkpoint(self, paper_id: str) -> bool:
        """Save the last processed paper ID to checkpoint file"""
        try:
            checkpoint_data = {
                "last_processed_id": paper_id,
                "timestamp": asyncio.get_event_loop().time(),
                "batch_size": self.batch_size,
            }

            async with aiofiles.open(self.checkpoint_file, "w") as f:
                await f.write(json.dumps(checkpoint_data, indent=2))

            self.last_processed_id = paper_id
            self.logger.info(f"Checkpoint saved: {paper_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}")
            return False

    @lru_cache(maxsize=1000)
    def normalize_category(self, category: str) -> str:
        """Normalize category with caching for better performance"""

        if category in self.category_cache:
            return self.category_cache[category]

        if category in self.legacy_to_current_mapping:
            mapped_category = self.legacy_to_current_mapping[category]
            self.category_cache[category] = mapped_category
            self.logger.debug(
                f"Mapped legacy category '{category}' to '{mapped_category}'"
            )
            return mapped_category

        if category in self.valid_categories:
            self.category_cache[category] = category
            return category

        for valid_cat in self.valid_categories:
            if category.startswith(valid_cat + ".") or category.startswith(
                valid_cat + "-"
            ):
                self.category_cache[category] = valid_cat
                return valid_cat

        self.category_cache[category] = category
        return category

    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if a string is in a valid date format (YYYY-MM-DD or similar)"""
        import re

        return bool(re.match(r"^\d{4}-\d{2}-\d{2}", date_str))

    def sanitize_arxiv_text(self, text: str, max_chars: int = 1500) -> str:
        """Sanitize arXiv text using precompiled regex patterns for better performance"""
        if not text or not isinstance(text, str):
            return ""

        try:
            text = " ".join(text.split())

            for name, pattern in self.latex_patterns.items():
                try:
                    text = pattern.sub("", text)
                except Exception as e:
                    self.logger.warning(f"Error applying {name} pattern: {e}")

            text = " ".join(text.split())

            return text[:max_chars]
        except Exception as e:
            self.logger.error(f"Error in sanitize_arxiv_text: {e}")
            return text[:max_chars] if text else ""

    async def _process_line(self, line: str) -> ExtractedPaper | None:
        """Process a single line of JSON data"""
        if not line or not isinstance(line, str):
            self.logger.warning("Received invalid line (empty or not a string)")
            return None

        if not line.strip():
            return None

        try:
            try:
                obj = orjson.loads(line)
                if not isinstance(obj, dict):
                    self.logger.warning(f"Skipping non-dict JSON object: {type(obj)}")
                    return None
            except orjson.JSONDecodeError as e:
                self.logger.error(f"Malformed JSON: {e} - Line: {line[:100]}...")
                return None

            try:
                paper_id = (
                    obj.get("id", "").strip() if isinstance(obj.get("id"), str) else ""
                )
                title = (
                    (obj.get("title") or "").strip()
                    if isinstance(obj.get("title"), str)
                    else ""
                )
                if title:
                    title = " ".join(title.split())
                abstract = (
                    (obj.get("abstract") or "").strip()
                    if isinstance(obj.get("abstract"), str)
                    else ""
                )
                categories_raw = (
                    obj.get("categories", "").strip()
                    if isinstance(obj.get("categories"), str)
                    else ""
                )
                update_date = (
                    obj.get("update_date", "").strip()
                    if isinstance(obj.get("update_date"), str)
                    else ""
                )

                authors_raw = obj.get("authors", "")
                authors_parsed = obj.get("authors_parsed", [])
                authors = []

                if isinstance(authors_parsed, list) and authors_parsed:
                    try:
                        authors = [
                            f"{author[1]} {author[0]}".strip()
                            if len(author) >= 2
                            else (author[0] if len(author) >= 1 else "Unknown")
                            for author in authors_parsed
                        ]
                    except Exception as e:
                        self.logger.warning(
                            f"Error processing authors_parsed for {paper_id}: {e}"
                        )

                if not authors and isinstance(authors_raw, str):
                    authors = [
                        author.strip()
                        for author in authors_raw.split(",")
                        if author.strip()
                    ]
                elif not authors and isinstance(authors_raw, list):
                    authors = [str(author).strip() for author in authors_raw if author]

                if not authors:
                    authors = ["Unknown"]

            except AttributeError as e:
                self.logger.error(
                    f"Type error in paper fields: {e} - Paper ID: {obj.get('id', 'unknown')}"
                )
                return None

            if not paper_id:
                self.logger.warning(f"Skipping paper with missing ID: {obj}")
                return None

            if not (title or abstract):
                self.logger.warning(
                    f"Skipping paper due to missing title AND abstract: {paper_id}"
                )
                return None

            categories = []
            try:
                if categories_raw:
                    category_set = set()
                    for cat in categories_raw.split():
                        if cat:
                            try:
                                normalized = self.normalize_category(cat.strip())
                                category_set.add(normalized)
                            except Exception as cat_error:
                                self.logger.warning(
                                    f"Error normalizing category '{cat}': {cat_error}"
                                )
                    categories = sorted(category_set)
            except Exception as cat_error:
                self.logger.error(
                    f"Error processing categories for {paper_id}: {cat_error}"
                )

            try:
                combined_text_raw = f"{title} {abstract}"
                combined_text = self.sanitize_arxiv_text(combined_text_raw)

                if not combined_text.strip():
                    self.logger.warning(
                        f"Paper {paper_id} has empty content after sanitization"
                    )
                    combined_text = title or abstract  # Use unsanitized as fallback
            except Exception as text_error:
                self.logger.error(f"Error sanitizing text for {paper_id}: {text_error}")
                combined_text = (
                    combined_text_raw[:1500] if combined_text_raw else title or abstract
                )

            if update_date and not self._is_valid_date_format(update_date):
                self.logger.warning(
                    f"Invalid date format for paper {paper_id}: {update_date}"
                )
                update_date = ""

            try:
                sanitized_abstract = (
                    self.sanitize_arxiv_text(abstract) if abstract else ""
                )
                sanitized_title = self.sanitize_arxiv_text(title) if title else ""

                return ExtractedPaper(
                    id=paper_id,
                    abstract=sanitized_abstract,
                    title=sanitized_title,
                    authors=authors,
                    categories=categories,
                    date_updated=update_date,
                )
            except Exception as model_error:
                self.logger.error(
                    f"Error creating ExtractedPaper for {paper_id}: {model_error}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Unexpected parsing error: {e} — Line: {line[:100]}...")
            return None

    async def parse_yield_batches(self) -> AsyncIterator[List[ExtractedPaper]]:
        """Parse the dataset file and yield batches of papers"""
        batch = []
        line_buffer = []
        buffer_size = min(1000, self.batch_size * 2)
        lines_processed = 0
        papers_extracted = 0
        skip_until_id = self.last_processed_id
        resume_mode = skip_until_id is not None

        try:
            if not os.path.exists(self.file_path):
                self.logger.error(f"Dataset file not found: {self.file_path}")
                return

            try:
                async with aiofiles.open(self.file_path) as f:
                    async for line in f:
                        lines_processed += 1

                        if resume_mode:
                            try:
                                obj = orjson.loads(line)
                                current_id = obj.get("id", "").strip()

                                if current_id == skip_until_id:
                                    self.logger.info(
                                        f"Found checkpoint ID: {skip_until_id}. Resuming from next paper."
                                    )
                                    resume_mode = False
                                    continue
                                elif skip_until_id and current_id:
                                    continue
                            except Exception as e:
                                self.logger.warning(
                                    f"Error checking paper ID during resume: {e}"
                                )
                                resume_mode = False

                        if not resume_mode:
                            line_buffer.append(line)

                        if len(line_buffer) >= buffer_size:
                            try:
                                tasks = [
                                    self._process_line(line) for line in line_buffer
                                ]
                                results = await asyncio.gather(
                                    *tasks, return_exceptions=True
                                )

                                last_id = None
                                for result in results:
                                    if isinstance(result, Exception):
                                        self.logger.error(
                                            f"Error processing line: {result}"
                                        )
                                        continue

                                    if result:
                                        papers_extracted += 1
                                        batch.append(result)
                                        last_id = result.id
                                        if len(batch) >= self.batch_size:
                                            self.logger.info(
                                                f"Yielding batch of {len(batch)} papers"
                                            )
                                            yield batch

                                            if last_id:
                                                await self.save_checkpoint(last_id)
                                            batch = []
                            except Exception as batch_error:
                                self.logger.error(
                                    f"Error processing batch: {batch_error}"
                                )

                            line_buffer = []
                            if lines_processed % 10000 == 0:
                                self.logger.info(
                                    f"Progress: {lines_processed} lines processed, "
                                    f"{papers_extracted} papers extracted"
                                )

                if line_buffer:
                    try:
                        tasks = [self._process_line(line) for line in line_buffer]
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        last_id = None
                        for result in results:
                            if isinstance(result, Exception):
                                self.logger.error(f"Error processing line: {result}")
                                continue

                            if result:
                                papers_extracted += 1
                                batch.append(result)
                                last_id = result.id
                                if len(batch) >= self.batch_size:
                                    self.logger.info(
                                        f"Yielding batch of {len(batch)} papers"
                                    )
                                    yield batch
                                    # Save checkpoint with the last ID in the batch
                                    if last_id:
                                        await self.save_checkpoint(last_id)
                                    batch = []
                    except Exception as final_batch_error:
                        self.logger.error(
                            f"Error processing final batch: {final_batch_error}"
                        )
                if batch:
                    self.logger.info(f"Yielding final batch of {len(batch)} papers")
                    yield batch
                    if batch and hasattr(batch[-1], "id"):
                        await self.save_checkpoint(batch[-1].id)

                self.logger.info(
                    f"Parsing complete: {lines_processed} lines processed, "
                    f"{papers_extracted} papers extracted"
                )

            except (IOError, PermissionError) as file_error:
                self.logger.error(f"Error opening dataset file: {file_error}")
        except Exception as e:
            self.logger.error(f"Unexpected error in parse_yield_batches: {e}")
            if batch:
                self.logger.info(
                    f"Yielding emergency batch of {len(batch)} papers after error"
                )
                yield batch
                if batch and hasattr(batch[-1], "id"):
                    await self.save_checkpoint(batch[-1].id)
