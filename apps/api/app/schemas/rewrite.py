"""逐段风格统一（F4）模型。"""

from pydantic import BaseModel, Field


class RewriteRequest(BaseModel):
    markdown: str = Field(min_length=1)


class RewriteSegment(BaseModel):
    id: int
    original: str
    rewritten: str
    changed: bool = False
    reason: str = ""


class RewriteResponse(BaseModel):
    segments: list[RewriteSegment] = Field(default_factory=list)
    changed_count: int = 0


class RewriteAssembleRequest(BaseModel):
    markdown: str = Field(min_length=1)
    segments: list[RewriteSegment]
    accepted: list[int] = Field(default_factory=list)


class RewriteAssembleResponse(BaseModel):
    markdown: str
    applied: int
