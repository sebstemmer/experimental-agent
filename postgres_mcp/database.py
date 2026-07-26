import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


engine = create_async_engine(require_env("DATABASE_URL"))


def get_database_session() -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False)


async def create_all_tables_on_start():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
