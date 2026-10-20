"""排版（F5）相关模型。"""

from pydantic import BaseModel, Field


class TemplateInfo(BaseModel):
    key: str
    name: str
    description: str
    toc: bool = True
    numbering: bool = True
    page_numbers: bool = True


class FormatRequest(BaseModel):
    markdown: str = Field(min_length=1)
    title: str = ""
    template: str = "academic"
    toc: bool | None = None
    numbering: bool | None = None
    page_numbers: bool | None = None


class ReferenceEntry(BaseModel):
    index: int
    original: str
    formatted: str
    type: str = "other"
    note: str = ""


class ReferenceRequest(BaseModel):
    markdown: str = Field(min_length=1)


class ReferenceResponse(BaseModel):
    found: bool
    heading: str = ""
    entries: list[ReferenceEntry] = Field(default_factory=list)
    markdown: str = ""
    notes: list[str] = Field(default_factory=list)
