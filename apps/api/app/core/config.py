"""应用配置。

所有环境变量在此集中声明、解析与校验，其它模块一律通过 settings 读取，
不要在业务代码里直接使用 os.environ。
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- 基础 ----------
    app_name: str = "参赛项目 API"
    app_env: Literal["local", "dev", "prod"] = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"

    # ---------- 数据库 ----------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "contest"
    postgres_password: str = "contest"
    postgres_db: str = "contest"
    # 若显式提供 DATABASE_URL，则优先使用（云端托管数据库常见）
    database_url: str | None = None

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"

    # ---------- 跨域 ----------
    # 同时放行 localhost 与 127.0.0.1：两种写法在浏览器里是不同来源。
    # NoDecode 表示"不要按 JSON 解析"，否则 CORS_ORIGINS=a,b 这种逗号写法会直接报错。
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # ---------- LLM ----------
    llm_provider: str = "openai_compatible"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    # 注意：当前为推理模型，会先输出思考过程再输出回答
    llm_model: str = "deepseek-flash"
    llm_timeout: int = 60
    # 额外请求头（JSON 字符串）。部分网关有路由要求，例如 OpenCode Zen 的
    # 订阅端点需要 x-opencode-session；值写 "__auto__" 表示进程启动时生成一个 UUID。
    llm_extra_headers: str = ""

    # ---------- 搜索 ----------
    search_provider: str = "deepseek"
    search_api_key: str = ""
    # DeepSeek 搜索 API 的基地址（不含 /search 或 /fetch）
    search_base_url: str = "https://api.deepseek.com/v1/tools"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """支持 CORS_ORIGINS 用逗号分隔的写法。"""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlalchemy_url(self) -> str:
        """异步驱动使用的数据库连接串。"""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
