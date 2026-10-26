"""v1 版本路由汇总：后续功能模块在此注册。"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analysis,
    citations,
    data_assistant,
    format,
    health,
    llm,
    merge,
    pipeline,
    projects,
    references,
    transition,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(merge.router)
api_router.include_router(analysis.router)
api_router.include_router(format.router)
api_router.include_router(transition.router)
api_router.include_router(references.router)
api_router.include_router(citations.router)
api_router.include_router(data_assistant.router)
api_router.include_router(projects.router)
api_router.include_router(pipeline.router)
