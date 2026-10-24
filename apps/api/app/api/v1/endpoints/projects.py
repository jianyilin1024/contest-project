"""分工记录（F2）接口：项目 / 成员 / 任务。"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.project import Member, Project, Task
from app.schemas.tasks import (
    MemberIn,
    MemberOut,
    ProjectBrief,
    ProjectIn,
    ProjectOut,
    TaskIn,
    TaskOut,
    TaskPatch,
)

router = APIRouter(tags=["projects"])
logger = logging.getLogger(__name__)

VALID_STATUS = {"todo", "doing", "done"}


def _task_out(task: Task, member_name: str = "") -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        section=task.section,
        status=task.status,
        due_date=task.due_date,
        note=task.note,
        member_id=task.member_id,
        member_name=member_name,
    )


def _project_out(project: Project) -> ProjectOut:
    names = {member.id: member.name for member in project.members}
    tasks = [_task_out(task, names.get(task.member_id or -1, "")) for task in project.tasks]
    stats = {
        "todo": sum(1 for task in tasks if task.status == "todo"),
        "doing": sum(1 for task in tasks if task.status == "doing"),
        "done": sum(1 for task in tasks if task.status == "done"),
        "members": len(project.members),
    }
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        members=[MemberOut(id=m.id, name=m.name, role=m.role) for m in project.members],
        tasks=tasks,
        stats=stats,
    )


async def _get_project(db: AsyncSession, project_id: int) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/projects", response_model=list[ProjectBrief], summary="项目列表")
async def list_projects(db: AsyncSession = Depends(get_db_session)) -> list[ProjectBrief]:
    result = await db.execute(select(Project).order_by(Project.id.desc()))
    projects = result.scalars().all()
    return [
        ProjectBrief(
            id=item.id,
            name=item.name,
            description=item.description,
            member_count=len(item.members),
            task_count=len(item.tasks),
            done_count=sum(1 for task in item.tasks if task.status == "done"),
        )
        for item in projects
    ]


@router.post("/projects", response_model=ProjectOut, summary="新建项目")
async def create_project(
    payload: ProjectIn, db: AsyncSession = Depends(get_db_session)
) -> ProjectOut:
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_out(project)


@router.get("/projects/{project_id}", response_model=ProjectOut, summary="项目详情")
async def get_project(
    project_id: int, db: AsyncSession = Depends(get_db_session)
) -> ProjectOut:
    return _project_out(await _get_project(db, project_id))


@router.delete("/projects/{project_id}", summary="删除项目")
async def delete_project(
    project_id: int, db: AsyncSession = Depends(get_db_session)
) -> dict:
    project = await _get_project(db, project_id)
    await db.delete(project)
    await db.commit()
    return {"deleted": project_id}


@router.post("/projects/{project_id}/members", response_model=MemberOut, summary="添加成员")
async def add_member(
    project_id: int, payload: MemberIn, db: AsyncSession = Depends(get_db_session)
) -> MemberOut:
    await _get_project(db, project_id)
    member = Member(project_id=project_id, name=payload.name.strip(), role=payload.role.strip())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return MemberOut(id=member.id, name=member.name, role=member.role)


@router.delete("/members/{member_id}", summary="移除成员")
async def delete_member(member_id: int, db: AsyncSession = Depends(get_db_session)) -> dict:
    member = await db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="成员不存在")
    await db.delete(member)
    await db.commit()
    return {"deleted": member_id}


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, summary="新建任务")
async def create_task(
    project_id: int, payload: TaskIn, db: AsyncSession = Depends(get_db_session)
) -> TaskOut:
    await _get_project(db, project_id)
    if payload.status not in VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"状态必须是 {sorted(VALID_STATUS)}")
    task = Task(
        project_id=project_id,
        member_id=payload.member_id,
        title=payload.title.strip(),
        section=payload.section.strip(),
        status=payload.status,
        due_date=payload.due_date,
        note=payload.note.strip(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    member_name = ""
    if task.member_id:
        member = await db.get(Member, task.member_id)
        member_name = member.name if member else ""
    return _task_out(task, member_name)


@router.patch("/tasks/{task_id}", response_model=TaskOut, summary="更新任务")
async def update_task(
    task_id: int, payload: TaskPatch, db: AsyncSession = Depends(get_db_session)
) -> TaskOut:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"状态必须是 {sorted(VALID_STATUS)}")
    for key, value in data.items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    member_name = ""
    if task.member_id:
        member = await db.get(Member, task.member_id)
        member_name = member.name if member else ""
    return _task_out(task, member_name)


@router.delete("/tasks/{task_id}", summary="删除任务")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db_session)) -> dict:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    await db.delete(task)
    await db.commit()
    return {"deleted": task_id}
