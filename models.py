from pydantic import BaseModel
from typing import List


class PaperMetadata(BaseModel):
    id: str
    title: str
    abstract: str


class PaperEntry(BaseModel):
    metadata: PaperMetadata
    vector: List[float]


class SearchResult(BaseModel):
    id: str
    score: float


class SemSearchResult(BaseModel):
    id: str
    score: float
    abstract: str
    title: str
    authors: str
    link: str
