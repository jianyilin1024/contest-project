"""过渡段落（F3）相关模型。"""

from pydantic import BaseModel, Field


class BlockOut(BaseModel):
    id: int
    kind: str
    level: int = 0
    text: str


class TransitionOption(BaseModel):
    id: str
    label: str
    text: str
    # 与下一节开头的最长公共子串长度；>=12 视为复述
    overlap: int = 0
    duplicate: bool = False


class BoundaryOut(BaseModel):
    id: str
    after_block_id: int
    before_block_id: int
    section_from: str
    section_to: str
    context_before: str = ""
    context_after: str = ""
    needs: bool = False
    reason: str = ""
    confidence: float = 0.0
    options: list[TransitionOption] = Field(default_factory=list)


class TransitionRequest(BaseModel):
    markdown: str = Field(min_length=1)
    title: str = ""


class TransitionResponse(BaseModel):
    title: str
    blocks: list[BlockOut] = Field(default_factory=list)
    boundaries: list[BoundaryOut] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
    elapsed_ms: int = 0


class InsertionIn(BaseModel):
    after_block_id: int
    text: str = Field(min_length=1)


class ApplyRequest(BaseModel):
    blocks: list[BlockOut] = Field(min_length=1)
    insertions: list[InsertionIn] = Field(default_factory=list)


class ApplyResponse(BaseModel):
    markdown: str
    inserted: int
