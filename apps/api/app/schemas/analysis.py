"""单文档 AI 分析的请求 / 响应模型。"""

from pydantic import BaseModel, Field


class SegmentOut(BaseModel):
    id: int
    section: str
    text: str
    chars: int
    features: dict = Field(default_factory=dict)


class AuthorshipGroup(BaseModel):
    id: str
    label: str
    features: list[str] = Field(default_factory=list)
    units: int = 0
    characters: int = 0
    avg_sentence: float = 0.0
    unit_ids: list[int] = Field(default_factory=list)


class Assignment(BaseModel):
    unit_id: int
    group_id: str
    confidence: float
    reason: str = ""
    section: str = ""
    preview: str = ""


class AuthorshipResult(BaseModel):
    heterogeneity: str
    conclusion: str
    groups: list[AuthorshipGroup] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)


class StyleIssue(BaseModel):
    type: str
    title: str
    detail: str
    examples: list[str] = Field(default_factory=list)
    suggestion: str = ""


class StyleAdvice(BaseModel):
    canonical_style: str
    issues: list[StyleIssue] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)


class LayoutConvention(BaseModel):
    aspect: str
    observation: str
    consistent: bool
    suggestion: str = ""


class LayoutResult(BaseModel):
    summary: str
    conventions: list[LayoutConvention] = Field(default_factory=list)
    facts: dict = Field(default_factory=dict)


class AnalysisStats(BaseModel):
    sections: int
    paragraphs: int
    characters: int
    units_total: int
    units_analyzed: int


class SingleAnalysisResponse(BaseModel):
    title: str
    filename: str
    stats: AnalysisStats
    authorship: AuthorshipResult
    style: StyleAdvice
    layout: LayoutResult
    segments: list[SegmentOut] = Field(default_factory=list)
    model: str = ""
    elapsed_ms: int = 0


class UnifySegmentIn(BaseModel):
    id: int
    section: str = ""
    text: str = Field(min_length=1)
    group_id: str = ""


class UnifyRequest(BaseModel):
    title: str = "归并稿"
    style_brief: str = ""
    segments: list[UnifySegmentIn] = Field(min_length=1)
    target_group: str | None = None


class UnifyResponse(BaseModel):
    markdown: str
    rewritten: int
    failed: int
    notes: list[str] = Field(default_factory=list)
