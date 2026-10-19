"""多部分整合（F1）的请求 / 响应模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class DocumentStat(BaseModel):
    filename: str
    author: str = ""
    headings: int
    characters: int


class MergeStats(BaseModel):
    documents: int
    sections: int
    sub_sections: int
    characters: int
    duplicates: int
    cross_duplicates: int
    term_conflicts: int
    per_document: list[DocumentStat] = Field(default_factory=list)


class OutlineNode(BaseModel):
    level: int
    number: str
    title: str
    source: str = ""
    characters: int = 0
    preview: str = ""


class DuplicateOccurrence(BaseModel):
    source: str
    author: str = ""
    section: str = ""


class DuplicateGroup(BaseModel):
    text: str
    length: int
    occurrences: list[DuplicateOccurrence] = Field(default_factory=list)
    cross_document: bool = False


class TermConflict(BaseModel):
    short: str
    long: str
    short_docs: list[str] = Field(default_factory=list)
    long_docs: list[str] = Field(default_factory=list)
    total: int = 0


class MergeResponse(BaseModel):
    title: str
    stats: MergeStats
    outline: list[OutlineNode] = Field(default_factory=list)
    duplicates: list[DuplicateGroup] = Field(default_factory=list)
    terms: list[TermConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    markdown: str


class ExportRequest(BaseModel):
    markdown: str = Field(min_length=1)
    title: str = "合并文稿"
    format: Literal["md", "docx"] = "md"
