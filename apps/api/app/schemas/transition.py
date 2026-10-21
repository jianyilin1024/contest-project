"""过渡段落（F3）相关模型。"""

from pydantic import BaseModel, Field


class BlockOut(BaseModel):
    id: int
    kind: str
    level: int = 0
    text: str


class DeAIInfo(BaseModel):
    """去 AI 味的处理结果。"""

    before_score: int = 100
    after_score: int = 100
    issues: list[str] = Field(default_factory=list)
    applied: bool = False
    original: str | None = None
    remaining: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)


class TransitionOption(BaseModel):
    id: str
    label: str
    text: str
    # 与下一节开头的最长公共子串长度；>=12 视为复述
    overlap: int = 0
    duplicate: bool = False
    deai: DeAIInfo | None = None


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
    # 是否对生成的备选做去 AI 味处理（默认开）
    deai: bool = True


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
