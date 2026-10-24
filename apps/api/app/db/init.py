"""数据库初始化：启动时建表。

比赛项目优先"开箱即用"，因此用 create_all 而不是 Alembic 迁移；
表结构稳定后再补迁移脚本。数据库不可用时只记录警告，不影响应用启动。
"""

import logging

from app.db.base import Base
from app.db.session import engine
from app.models import project as _project  # noqa: F401  注册模型

logger = logging.getLogger(__name__)


async def init_models() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表检查完成")
    except Exception as exc:  # noqa: BLE001 - 数据库不可用时不应阻断启动
        logger.warning("数据库初始化失败（功能受限）：%s", exc)
