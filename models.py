from typing import List
from pydantic import BaseModel
from enum import Enum


class ArxivDomains(str, Enum):
    CS = "cs"
    ECON = "econ"
    EESS = "eess"
    MATH = "math"
    ASTRO_PH = "astro-ph"
    COND_MAT = "cond-mat"
    GR_QC = "gr-qc"
    HEP = "hep"
    MATH_PH = "math-ph"
    NUCL = "nucl"
    QUANT_PH = "quant-ph"
    PHYSICS = "physics"
    Q_BIO = "q-bio"
    Q_FIN = "q-fin"
    STAT = "stat"
    NLIN = "nlin"


class PaperExtracted(BaseModel):
    id: str
    abstract_title: str
    categories: List[ArxivDomains]
    date_published: str


class PaperToStore(BaseModel):
    id: str
    embedding: List[float]
    categories: List[ArxivDomains]
    date_published: str


class PaperMetadata(BaseModel):
    categories: List[str]
    date_published: int


class SearchResultItem(BaseModel):
    id: str
    distance: float
    metadata: PaperMetadata


class SearchResults(BaseModel):
    results: List[SearchResultItem]
