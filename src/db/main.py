from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import Config

async_engine = create_async_engine(url=Config.DATABASE_URL, echo=True)


async def init_db():
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)

        await conn.run_sync(
            SQLModel.metadata.create_all
        )  # used sync cos it doesn't execute asynchronously


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with Session() as session:
        yield session
