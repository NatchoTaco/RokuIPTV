from __future__ import annotations

from collections.abc import Callable

import redis
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from streamforge_api.api import api_router
from streamforge_api.core.config import Settings, get_settings
from streamforge_api.core.errors import StreamForgeError
from streamforge_api.core.logging import configure_logging, request_logging_middleware
from streamforge_api.core.redaction import redact_payload
from streamforge_api.db.session import create_engine_from_settings, create_session_factory


def create_app(
    settings: Settings | None = None,
    session_factory: Callable[[], Session] | None = None,
    redis_client: object | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app_settings.validate_runtime()
    configure_logging(app_settings.log_level)

    app = FastAPI(title=f"{app_settings.app_name} API", version=app_settings.version)
    app.state.settings = app_settings

    if session_factory is None:
        engine = create_engine_from_settings(app_settings)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
    else:
        app.state.db_session_factory = session_factory

    app.state.redis_client = redis_client
    if redis_client is None:
        app.state.redis_client = redis.Redis.from_url(
            app_settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    app.middleware("http")(request_logging_middleware)
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(StreamForgeError)
    async def streamforge_error_handler(_request: Request, exc: StreamForgeError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.public_message})

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": jsonable_encoder(redact_payload(exc.errors()))},
        )

    return app


app = create_app()
