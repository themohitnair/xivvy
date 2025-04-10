import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from typing import List
from models import SearchResult, SemSearchResult


class Lucy:  # GothamChess's Wife
    def __init__(self, results: List[SearchResult]):
        self.results = results
        self.base_url = "http://export.arxiv.org/api/query?id_list="

    async def fetch_metadata(
        self, session: aiohttp.ClientSession, result: SearchResult
    ):
        async with session.get(f"{self.base_url}{result.id}") as resp:
            text = await resp.text()
            root = ET.fromstring(text)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")
            if entry is None:
                return None

            title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
            abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
            authors = entry.findall("{http://www.w3.org/2005/Atom}author")
            author_names = ", ".join(
                [
                    author.find("{http://www.w3.org/2005/Atom}name").text.strip()
                    for author in authors
                ]
            )
            link = (
                entry.find("{http://www.w3.org/2005/Atom}id").text.replace("abs", "pdf")
                + ".pdf"
            )

            return SemSearchResult(
                id=result.id,
                score=result.score,
                title=title,
                abstract=abstract,
                authors=author_names,
                link=link,
            )

    async def get_semantic_results(self) -> List[SemSearchResult]:
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_metadata(session, result) for result in self.results]
            enriched = await asyncio.gather(*tasks)
        return [r for r in enriched if r is not None]
