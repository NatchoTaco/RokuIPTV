from __future__ import annotations

from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from streamforge_api.core.config import Settings
from streamforge_api.models import SetupState
from streamforge_api.schemas.health import HealthResponse, ServiceCheck


class RedisClient(Protocol):
    def ping(self) -> bool:
        ...


class HealthService:
    def __init__(self, db: Session, settings: Settings, redis_client: RedisClient | None) -> None:
        self.db = db
        self.settings = settings
        self.redis_client = redis_client

    def collect(self) -> HealthResponse:
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
        }
        setup_complete = False
        try:
            setup_state = self.db.scalar(select(SetupState).limit(1))
            setup_complete = setup_state.is_complete if setup_state is not None else False
        except Exception:
            checks["setup_state"] = ServiceCheck(status="error", detail="setup state unavailable")
        else:
            checks["setup_state"] = ServiceCheck(status="ok", detail="setup state available")

        status = "ok" if all(check.status == "ok" for check in checks.values()) else "degraded"
        return HealthResponse(
            status=status,
            service=self.settings.app_name,
            version=self.settings.version,
            environment=self.settings.env,
            setup_complete=setup_complete,
            checks=checks,
        )

    def _check_database(self) -> ServiceCheck:
        try:
            self.db.execute(text("select 1"))
        except Exception:
            return ServiceCheck(status="error", detail="database query failed")
        return ServiceCheck(status="ok", detail="database reachable")

    def _check_redis(self) -> ServiceCheck:
        if self.redis_client is None:
            return ServiceCheck(status="error", detail="redis client not configured")
        try:
            self.redis_client.ping()
        except Exception:
            return ServiceCheck(status="error", detail="redis ping failed")
        return ServiceCheck(status="ok", detail="redis reachable")
