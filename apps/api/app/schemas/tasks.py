"""分工记录（F2）模型。"""

from datetime import date

from pydantic import BaseModel, Field


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    role: str = Field(default="成员", max_length=30)


class MemberOut(BaseModel):
    id: int
    name: str
    role: str


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    section: str = ""
    member_id: int | None = None
    status: str = "todo"
    due_date: date | None = None
    note: str = ""


class TaskPatch(BaseModel):
    title: str | None = None
    section: str | None = None
    member_id: int | None = None
    status: str | None = None
    due_date: date | None = None
    note: str | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    section: str
    status: str
    due_date: date | None = None
    note: str
    member_id: int | None = None
    member_name: str = ""


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    members: list[MemberOut] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class ProjectBrief(BaseModel):
    id: int
    name: str
    description: str
    member_count: int = 0
    task_count: int = 0
    done_count: int = 0
