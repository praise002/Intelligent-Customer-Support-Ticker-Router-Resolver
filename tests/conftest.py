import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import jwt
import pytest
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src import app
from src.auth.schemas import UserCreate
from src.config import Config
from src.db.main import get_session
from src.db.models import Profile, ProfileSkill, Project, Review, Skill, Tag
from src.profiles.service import ProfileService
from src.projects.service import ProjectService


@pytest.fixture(scope="session")
async def redis_client():
    """
    Provides a fake Redis client for testing.
    """
    fake_redis = FakeAsyncRedis(decode_responses=True)
    yield fake_redis
    await fake_redis.aclose()


@pytest.fixture(autouse=True)
async def mock_redis(monkeypatch, redis_client):
    """
    Automatically mocks Redis for all tests.
    autouse=True means this runs for every test without needing to specify it.
    """
    # Mock the token_blocklist that's created at module level
    from src.db import redis

    monkeypatch.setattr(redis, "token_blocklist", redis_client)

    yield

    # Clear Redis after each test for isolation
    await redis_client.flushall()


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
def mock_email(monkeypatch):
    """
    Mocks the send_email_by_type function to prevent real emails during tests.

    Returns:
        list: List of "sent" emails that can be verified in tests
    """
    sent_emails = []

    def fake_send_email_by_type(
        background_tasks,
        email_type: str,
        email_to: str,
        name: str,
        otp: str = None,
    ):
        """Fake send_email_by_type that stores email details."""

        from src.mail import get_email_template_data

        email_data = get_email_template_data(email_type)

        template_context = {"name": name}
        if otp:
            template_context["otp"] = str(otp)

        sent_emails.append(
            {
                "subject": email_data["subject"],
                "email_to": email_to,
                "template_context": template_context,
                "template_name": email_data["template_name"],
            }
        )

    from src.auth import routes

    monkeypatch.setattr(routes, "send_email_by_type", fake_send_email_by_type)

    return sent_emails


@pytest.fixture
def mock_otp(monkeypatch):
    """
    Mocks OTP generation to return predictable test value.

    Returns:
        int: The predictable OTP that will be "generated"
    """

    async def fake_generate_otp(user, session):
        return 123456

    from src.auth import routes

    monkeypatch.setattr(routes, "generate_otp", fake_generate_otp)

    return 123456


@pytest.fixture
def valid_user_data():
    """
    Provides valid user registration data.

    Returns:
        dict: Valid user registration data
    """
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePass123!",
    }


@pytest.fixture
def another_user_data():
    """
    Provides different user data for testing multiple users.

    Returns:
        dict: Another set of valid user data
    """
    return {
        "email": "another@example.com",
        "username": "anotheruser",
        "first_name": "Another",
        "last_name": "User",
        "password": "AnotherPass123!",
    }


@pytest.fixture
def user2_data():
    return {
        "email": "user2@example.com",
        "username": "user2",
        "first_name": "Test",
        "last_name": "User2",
        "password": "SecurePass123!",
    }


@pytest.fixture
def user3_data():
    return {
        "email": "user3@example.com",
        "username": "user3",
        "first_name": "Test",
        "last_name": "User3",
        "password": "SecurePass123!",
    }


@pytest.fixture
def invalid_user_data():
    return {
        "email": "invalid-email",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePass123!",
    }


@pytest.fixture
def weak_password_data():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "123",
    }


@pytest.fixture
async def registered_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user2_data: dict,
):
    """
    Creates a registered but unverified user for testing.
    """
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**user2_data)
    user = await user_service.create_user(user_create, db_session)
    return user


@pytest.fixture
async def verified_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user3_data: dict,
):
    """
    Creates a verified user for testing.
    """
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**user3_data)
    user = await user_service.create_user(user_create, db_session)

    await user_service.update_user(user, {"is_email_verified": True}, db_session)
    return user


@pytest.fixture
async def another_verified_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    valid_user_data: dict,
):
    """
    Creates a verified user for testing.
    """
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**valid_user_data)
    user = await user_service.create_user(user_create, db_session)

    await user_service.update_user(user, {"is_email_verified": True}, db_session)
    return user


@pytest.fixture
async def inactive_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    another_user_data: dict,
):

    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**another_user_data)
    user = await user_service.create_user(user_create, db_session)

    await user_service.update_user(
        user, {"is_email_verified": True, "is_active": False}, db_session
    )
    return user


@pytest.fixture
async def otp_for_user(
    db_session: AsyncSession,
    registered_user,
    mock_otp: str,
):
    """
    Creates a valid OTP for a user.
    """

    from src.db.models import Otp

    # Create OTP record directly
    otp_record = Otp(user_id=registered_user.id, otp=mock_otp, is_valid=True)
    db_session.add(otp_record)
    await db_session.commit()

    return mock_otp


@pytest.fixture
def expired_refresh_token():
    """Generate an expired refresh token for testing"""
    now = datetime.now(timezone.utc)
    user_data = {
        "user": {
            "email": "test@example.com",
            "user_id": "test-user-id",
            "role": "user",
        },
        "iat": now,
        "exp": now - timedelta(hours=1),  # Expired 1 hour ago
        "jti": "expired-token-jti",
        "token_type": "refresh",
    }

    expired_token = jwt.encode(
        user_data,
        Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM,
    )

    return expired_token


@pytest.fixture
def expired_access_token():
    """Generate an expired access token for testing"""
    now = datetime.now(timezone.utc)
    user_data = {
        "user": {
            "email": "test@example.com",
            "user_id": "test-user-id",
            "role": "user",
        },
        "iat": now,
        "exp": datetime.now(timezone.utc)
        - timedelta(minutes=30),  # Expired 30 mins ago
        "jti": "expired-access-token-jti",
        "token_type": "access",
    }

    expired_token = jwt.encode(
        user_data,
        Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM,
    )

    return expired_token


@pytest.fixture
async def profile_service():
    """Returns ProfileService instance"""
    return ProfileService()


@pytest.fixture
async def verified_user_with_profile(verified_user, db_session: AsyncSession):
    """
    Returns verified user with their profile.
    Profile is automatically created via relationship.
    """
    # The profile should already exist due to the relationship
    # But let's ensure it's loaded
    from sqlmodel import select

    statement = select(Profile).where(Profile.user_id == verified_user.id)
    result = await db_session.exec(statement)
    profile = result.first()

    return {"user": verified_user, "profile": profile}


@pytest.fixture
async def another_verified_user_with_profile(
    async_client: AsyncClient,
    db_session: AsyncSession,
    another_user_data: dict,
):
    """
    Creates a second verified user for testing interactions between users.
    """
    from src.auth.schemas import UserCreate
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**another_user_data)
    user = await user_service.create_user(user_create, db_session)
    await user_service.update_user(user, {"is_email_verified": True}, db_session)

    # Get profile
    from sqlmodel import select

    statement = select(Profile).where(Profile.user_id == user.id)
    result = await db_session.exec(statement)
    profile = result.first()

    return {"user": user, "profile": profile}


@pytest.fixture
async def sample_skills(db_session: AsyncSession):
    """
    Creates sample skills in the database.
    """
    skills_data = [
        {"name": "Python"},
        {"name": "JavaScript"},
        {"name": "React"},
        {"name": "Django"},
        {"name": "PostgreSQL"},
    ]

    skills = []
    for skill_data in skills_data:
        skill = Skill(**skill_data)
        db_session.add(skill)
        skills.append(skill)

    await db_session.commit()

    return skills


@pytest.fixture
async def profile_with_skills(
    verified_user_with_profile,
    sample_skills,
    db_session: AsyncSession,
):
    """
    Creates a profile with multiple skills.
    """
    profile = verified_user_with_profile["profile"]

    # Add first 3 skills to the profile
    for i in range(3):
        profile_skill = ProfileSkill(
            profile_id=profile.id,
            skill_id=sample_skills[i].id,
            description=f"Expert in {sample_skills[i].name}",
        )
        db_session.add(profile_skill)

    await db_session.commit()

    return {"profile": profile, "user": verified_user_with_profile["user"]}


@pytest.fixture
def mock_cloudinary(monkeypatch):
    """
    Mocks Cloudinary upload and delete operations.
    """
    upload_result_url = (
        "https://res.cloudinary.com/test/image/upload/v123/test_avatar.jpg"
    )

    # Wrap in staticmethod to match the original
    @staticmethod
    async def fake_upload_image(file, folder="avatars", public_id=None, overwrite=True):
        """Mock upload"""
        return upload_result_url

    @staticmethod
    async def fake_delete_image(public_id):
        """Mock delete"""
        return True

    @staticmethod
    def fake_extract_public_id(url):
        """Mock extract"""
        return "test_avatar"

    from src.cloudinary_service import CloudinaryService

    # Set the static methods directly
    monkeypatch.setattr(CloudinaryService, "upload_image", fake_upload_image)
    monkeypatch.setattr(CloudinaryService, "delete_image", fake_delete_image)
    monkeypatch.setattr(
        CloudinaryService, "extract_public_id_from_url", fake_extract_public_id
    )

    return {"url": upload_result_url, "public_id": "test_avatar"}


@pytest.fixture
async def project_service():
    """Returns ProjectService instance"""
    return ProjectService()


@pytest.fixture
async def sample_project(
    verified_user_with_profile,
    db_session: AsyncSession,
):
    """
    Creates a sample project owned by verified_user.
    """
    profile = verified_user_with_profile["profile"]

    project = Project(
        title="My Awesome Project",
        slug="my-awesome-project",
        description="This is a test project for unit testing",
        featured_image="https://example.com/image.jpg",
        source_link="https://github.com/user/project",
        demo_link="https://project-demo.com",
        owner_id=profile.id,
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.fixture
async def another_user_project(
    another_verified_user_with_profile,
    db_session: AsyncSession,
):
    """
    Creates a project owned by another_verified_user.
    """
    profile = another_verified_user_with_profile["profile"]

    project = Project(
        title="Another User's Project",
        slug="another-users-project",
        description="Project owned by a different user",
        featured_image="https://example.com/another-image.jpg",
        owner_id=profile.id,
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.fixture
async def sample_tags(db_session: AsyncSession, sample_project):
    """
    Creates sample tags linked to a project.
    """
    tags_data = [
        {"name": "React", "project_id": sample_project.id},
        {"name": "TypeScript", "project_id": sample_project.id},
        {"name": "Node.js", "project_id": sample_project.id},
    ]

    tags = []
    for tag_data in tags_data:
        tag = Tag(**tag_data)
        db_session.add(tag)
        tags.append(tag)

    await db_session.commit()

    return tags


@pytest.fixture
async def project_with_tags(sample_project, sample_tags, db_session: AsyncSession):
    """
    Returns a project that has tags.
    """
    # Refresh to load relationships
    statement = (
        select(Project)
        .options(selectinload(Project.tags))
        .where(Project.id == sample_project.id)
    )
    result = await db_session.exec(statement)
    project = result.first()

    return project


@pytest.fixture
async def project_with_reviews(
    sample_project,
    another_verified_user_with_profile,
    db_session: AsyncSession,
):
    """
    Creates a project with reviews from other users.
    """
    from src.constants import VoteType

    reviewer_profile = another_verified_user_with_profile["profile"]

    review = Review(
        project_id=sample_project.id,
        profile_id=reviewer_profile.id,
        value=VoteType.up,
        content="Great project! Very helpful.",
    )

    db_session.add(review)
    await db_session.commit()

    # Refresh project with reviews
    statement = (
        select(Project)
        .options(selectinload(Project.reviews))
        .where(Project.id == sample_project.id)
    )
    result = await db_session.exec(statement)
    project = result.first()

    return project


@pytest.fixture
async def multiple_projects(
    verified_user_with_profile,
    another_verified_user_with_profile,
    db_session: AsyncSession,
):
    """
    Creates multiple projects for testing pagination and search.
    """
    profile1 = verified_user_with_profile["profile"]
    profile2 = another_verified_user_with_profile["profile"]

    projects_data = [
        {
            "title": "Python Web Scraper",
            "slug": "python-web-scraper",
            "description": "A web scraping tool built with Python",
            "featured_image": "https://example.com/scraper.jpg",
            "owner_id": profile1.id,
        },
        {
            "title": "React Dashboard",
            "slug": "react-dashboard",
            "description": "Modern admin dashboard with React",
            "featured_image": "https://example.com/dashboard.jpg",
            "owner_id": profile2.id,
        },
        {
            "title": "Django REST API",
            "slug": "django-rest-api",
            "description": "RESTful API using Django framework",
            "featured_image": "https://example.com/api.jpg",
            "owner_id": profile1.id,
        },
    ]

    projects = []
    for project_data in projects_data:
        project = Project(**project_data)
        db_session.add(project)
        projects.append(project)

    await db_session.commit()

    return projects
