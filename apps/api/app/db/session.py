"""异步数据库引擎与会话工厂。

引擎在导入时创建但不建立连接，因此没有数据库时应用依然可以启动
（健康检查会如实报告数据库不可用）。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.sqlalchemy_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：按请求提供数据库会话。"""
    async with SessionLocal() as session:
        yield session
