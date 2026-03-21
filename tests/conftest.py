import asyncio
import json
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from zipp import Path

from src import app
from src.config import Config
from src.db.main import get_session

# Create async engine
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,  # Set to True to see SQL queries in development
    future=True,
)

# Create async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    Dependency function that yields database sessions.
    """
    async with SessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    """
    Creates an event loop for the entire test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgresql_proc_config():
    """
    Configure how pytest-postgresql starts the PostgreSQL process.
    """
    return {
        "port": None,  # Random port
        "host": "localhost",
        "user": "postgres",
        "password": "",
        "options": "-c fsync=off",  # Faster for testing
    }


@pytest.fixture(scope="session")
async def database_url(postgresql_proc):
    """
    Constructs the async database URL for the temporary database and creates it.
    """
    from sqlalchemy_utils import create_database, database_exists

    # Extract connection details from postgresql_proc fixture
    user = postgresql_proc.user
    host = postgresql_proc.host
    port = postgresql_proc.port
    dbname = postgresql_proc.dbname
    password = postgresql_proc.password if hasattr(postgresql_proc, "password") else ""

    # Construct sync URL for database creation
    sync_url = (
        f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        if password
        else f"postgresql://{user}@{host}:{port}/{dbname}"
    )

    # Create the database if it doesn't exist
    if not database_exists(sync_url):
        create_database(sync_url)

    # Construct and return async URL for the engine (using psycopg instead of asyncpg)
    async_url = (
        f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        if password
        else f"postgresql+psycopg://{user}@{host}:{port}/{dbname}"
    )

    return async_url


@pytest.fixture(scope="session")
async def test_engine(database_url):
    """
    Creates async SQLAlchemy engine connected to temporary database.

    Args:
        database_url: URL from database_url fixture

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True to see SQL queries
        poolclass=NullPool,  # Don't pool connections in tests
        future=True,
    )

    yield engine

    # Dispose engine
    await engine.dispose()


@pytest.fixture
async def database(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a fresh database with clean tables for each test.
    """
    # Drop and recreate all tables before each test
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def client(database: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Creates an async HTTP client for testing API endpoints.

    Args:
        database: Database session from database fixture

    Yields:
        AsyncClient: HTTP client for making requests
    """

    # Override the database dependency
    async def override_get_db():
        yield database

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test/api/v6",
    ) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
async def test_engine(database_url):
    """
    Creates async SQLAlchemy engine connected to temporary database.

    Args:
        database_url: URL from database_url fixture

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True to see SQL queries (useful for debugging)
        poolclass=NullPool,  # Don't pool connections in tests
        future=True,
    )

    yield engine

    # Dispose engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a fresh database with clean tables for each test.
    """
    # Drop and recreate all tables before each test
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Creates an async HTTP client for testing API endpoints.



    Args:
        db_session: Database session from db_session fixture

    Yields:
        AsyncClient: HTTP client for making requests
    """

    # Override the database dependency
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def test_tickets():
    """Load test tickets from JSON fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "demo_tickets.json"
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture
def sample_ticket():
    """Single ticket for quick tests"""
    return {
        "ticket_id": "TKT-10001",
        "subject": "Naira withdrawal stuck on 'processing' for 8+ hours",
        "description": "I initiated a withdrawal to my GTBank account this morning at 8am and it's still showing 'processing'. It's now 5pm. Normally withdrawals are instant. I need this money urgently. Transaction ID: WD-NGN-8472910. This has never happened before in the 2 years I've been using Raenest.",
        "issue_type": "transfers",
        "urgency": "high",
    }


# TODO: DB STUFFS NOT NEEDED FOR TESTING, REMOVE IT
