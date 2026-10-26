"""引用建议模型。"""

from pydantic import BaseModel, Field


class CitationCandidate(BaseModel):
    index: int
    text: str
    bibtex: str = ""
    title: str = ""
    year: int | None = None
    venue: str = ""
    doi: str = ""


class CitationSpot(BaseModel):
    sentence: str
    reason: str
    query: str
    candidates: list[CitationCandidate] = Field(default_factory=list)


class CitationSuggestResponse(BaseModel):
    spots: list[CitationSpot] = Field(default_factory=list)
    total: int = 0
    scanned_paragraphs: int = 0
