from fastapi import APIRouter

from streamforge_api.api.routes import auth, channels, cleanup, diagnostics, health, playlists, settings, setup, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(setup.router, prefix="/setup", tags=["setup"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(cleanup.router, prefix="/cleanup", tags=["cleanup"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])
