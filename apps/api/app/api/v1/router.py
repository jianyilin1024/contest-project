"""v1 版本路由汇总：后续功能模块在此注册。"""

from fastapi import APIRouter

from app.api.v1.endpoints import analysis, format, health, llm, merge

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(merge.router)
api_router.include_router(analysis.router)
api_router.include_router(format.router)

# 后续阶段在此追加：
# api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# api_router.include_router(references.router, prefix="/references", tags=["references"])
