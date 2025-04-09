from pydantic import BaseModel
from typing import List


class PaperMetadata(BaseModel):
    id: str
    title: str
    abstract: str
    authors: List[str]


class PaperEntry(BaseModel):
    metadata: PaperMetadata
    vector: List[float]
