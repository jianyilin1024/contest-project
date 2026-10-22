"""参考文献检索（F7）模型。"""

from pydantic import BaseModel, Field


class ReferenceRecordOut(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    kind: str = "other"
    source: str = ""
    cited_by: int = 0
    abstract: str = ""


class ReferenceEntryOut(BaseModel):
    index: int
    text: str
    record: ReferenceRecordOut


class ReferenceSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=20)


class ReferenceSearchResponse(BaseModel):
    query: str
    total: int
    entries: list[ReferenceEntryOut] = Field(default_factory=list)


class ReferenceInsertRequest(BaseModel):
    markdown: str = Field(min_length=1)
    entries: list[str] = Field(min_length=1)


class ReferenceInsertResponse(BaseModel):
    markdown: str
    inserted: int
