from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from streamforge_api import models as _models  # noqa: F401
from streamforge_api.core.config import Settings
from streamforge_api.db.base import Base
from streamforge_api.main import create_app


class FakeRedis:
    def ping(self) -> bool:
        return True


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = Settings(
        secret_key="test-secret-key-for-streamforge",
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        cors_origins="http://localhost:5173",
    )

    app = create_app(
        settings=settings,
        session_factory=session_factory,
        redis_client=FakeRedis(),
    )
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(client: TestClient) -> Generator[Session]:
    session_factory = client.app.state.db_session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
