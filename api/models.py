from typing import Optional, List
from pydantic import BaseModel, Field
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


class PaperMetadata(BaseModel):
    paper_id: str = Field(..., description="Unique identifier for the paper")
    categories: List[str] = Field(
        default_factory=list, description="List of paper categories"
    )
    authors: List[str] = Field(default_factory=list, description="List of authors")
    title: str = Field(..., description="Paper title")
    date_updated: str = Field(
        ..., description="ISO-formatted date when the paper was last updated"
    )


class SearchResult(BaseModel):
    distance: Optional[float] = Field(
        default=None, description="Similarity distance score (lower is better)"
    )
    metadata: PaperMetadata = Field(..., description="Metadata about the paper")

    class Config:
        json_schema_extra = {
            "example": {
                "distance": 0.25,
                "metadata": {
                    "paper_id": "1234.5678",
                    "categories": ["cs", "math"],
                    "authors": ["Author One", "Author Two"],
                    "title": "Example Paper Title",
                    "date_updated": "2023-01-01",
                },
            }
        }
