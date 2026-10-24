"""数据助手（F6）模型。"""

from pydantic import BaseModel, Field


class GapOut(BaseModel):
    description: str
    query: str


class SuggestionOut(BaseModel):
    value: str
    context: str = ""
    source_title: str = ""
    source_url: str
    quote: str = ""
    confidence: float = 0.5
    gap: str = ""


class DataAssistRequest(BaseModel):
    text: str = Field(min_length=10)


class DataAssistResponse(BaseModel):
    gaps: list[GapOut] = Field(default_factory=list)
    suggestions: list[SuggestionOut] = Field(default_factory=list)
    searched: int = 0
