"""
Database definitions.

| ``Path``: _db_definitions.py
| ``Project``: SquadronServer
| ``Created``: 23/11/2026
| ``Authors``: Nilusink
"""
from sqlalchemy.ext.asyncio import create_async_engine, \
    AsyncSession, async_sessionmaker
from collections.abc import AsyncGenerator
from sqlmodel import SQLModel, Field
from sqlalchemy import Connection
import time

from ._constants import DB_FILE, Status
from ._alerts import PriorityLevel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    status: Status = Status.offline
    info: str = ""


class Alert(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    priority_level: PriorityLevel
    title: str
    time: int = Field(default_factory=lambda: time.time())
    info: str | None = None

    alerted_by: int = Field(foreign_key="user.id")


class AlertTarget(SQLModel, table=True):
    alert_id: int = Field(
        foreign_key="alert.id",
        primary_key=True
    )

    user_id: int = Field(
        foreign_key="user.id",
        primary_key=True
    )

    executed: bool = False


def __create_tables(conn: Connection) -> None:
    SQLModel.metadata.create_all(conn)


async def init_db() -> None:
    """check create all tables"""
    async with ENGINE.begin() as conn:
        await conn.run_sync(__create_tables)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# global session creater
ENGINE = create_async_engine(f"sqlite+aiosqlite:///{DB_FILE}")

SessionLocal = async_sessionmaker(
    ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
)