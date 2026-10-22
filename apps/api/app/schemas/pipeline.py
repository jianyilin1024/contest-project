"""一键成稿流水线模型。"""

from pydantic import BaseModel, Field


class StepOut(BaseModel):
    name: str
    status: str  # ok | skipped | failed
    detail: str = ""
    elapsed_ms: int = 0


class OneClickResponse(BaseModel):
    title: str
    merged_markdown: str
    final_markdown: str
    stats: dict = Field(default_factory=dict)
    duplicates: list[dict] = Field(default_factory=list)
    terms: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    transitions: dict = Field(default_factory=dict)
    references: dict = Field(default_factory=dict)
    steps: list[StepOut] = Field(default_factory=list)
    elapsed_ms: int = 0
