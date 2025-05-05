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


class ExtractedPaper(BaseModel):
    id: str
    abstract_title: str
    categories: List[ArxivDomains]
    date_updated: str


class StoredPaper(BaseModel):
    paper_id: str
    embedding: List[float]
    categories: List[ArxivDomains]
    date_updated: str


class StoredPaperMetadata(BaseModel):
    paper_id: str
    categories: List[str]
    date_updated: int


class PaperMetadata(BaseModel):
    paper_id: str
    categories: List[str]
    date_updated: str


class SearchResult(BaseModel):
    distance: float
    metadata: PaperMetadata
