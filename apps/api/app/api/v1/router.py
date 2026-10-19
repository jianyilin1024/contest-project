"""v1 版本路由汇总：后续功能模块在此注册。"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)

# 后续阶段在此追加：
# api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
# api_router.include_router(sections.router, prefix="/sections", tags=["sections"])
# api_router.include_router(references.router, prefix="/references", tags=["references"])
