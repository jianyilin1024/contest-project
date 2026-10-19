"""健康检查端点。

/health        存活探针（不依赖外部组件）
/health/ready  就绪探针（检查数据库与 Redis）
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", summary="存活探针")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env, "version": "0.1.0"}


@router.get("/health/ready", summary="就绪探针")
async def ready(db: Annotated[AsyncSession, Depends(get_db_session)]) -> dict:
    checks: dict[str, str] = {"database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - 探针需要吞掉异常并如实上报
        checks["database"] = f"error: {type(exc).__name__}"

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {type(exc).__name__}"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
