from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from streamforge_api.core.config import Settings


def create_engine_from_settings(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    pool_kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
            pool_kwargs["poolclass"] = StaticPool
    return create_engine(settings.database_url, connect_args=connect_args, **pool_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
