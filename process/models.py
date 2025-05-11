from typing import List
from pydantic import BaseModel, Field, field_validator
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
    id: str = Field(..., description="Unique identifier for the paper")
    abstract: str = Field(default="", description="Paper abstract")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    categories: List[ArxivDomains] = Field(
        default_factory=list, description="List of paper categories"
    )
    date_updated: str = Field(
        default="", description="Date when the paper was last updated"
    )

    @field_validator("id")
    def id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("id cannot be empty")
        return v.strip()

    @field_validator("title")
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()


class StoredPaper(BaseModel):
    paper_id: str = Field(..., description="Unique identifier for the paper")
    embedding: List[float] = Field(
        ..., description="Vector embedding of the paper content"
    )
    categories: List[ArxivDomains] = Field(
        default_factory=list, description="List of paper categories"
    )
    authors: List[str] = Field(default_factory=list, description="List of authors")
    title: str = Field(..., description="Paper title")
    date_updated: str = Field(
        default="", description="Date when the paper was last updated"
    )

    @field_validator("paper_id")
    def paper_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("paper_id cannot be empty")
        return v.strip()

    @field_validator("title")
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("embedding")
    def embedding_must_not_be_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("embedding cannot be empty")
        return v
