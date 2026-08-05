# StreamForge

StreamForge is a private, self-hosted television management and Roku playback platform. The current implementation is limited to Milestones 1 and 2 from `STREAMFORGE_SPEC.md`.

## Milestone 1

Implemented scope:

- Monorepo foundation.
- FastAPI backend with PostgreSQL persistence.
- Redis readiness integration.
- Alembic migrations.
- Administrator bootstrap, sign in, sign out, and current-user endpoints.
- Persisted first-run state.
- React dashboard with setup and health screens.
- Docker Compose local stack.

Deferred scope is tracked in `docs/development-roadmap.md`.

## Milestone 2

Implemented scope:

- Sources dashboard page.
- Add Source wizard for remote M3U URL and uploaded M3U files.
- Safe source validation with channel count, group count, warnings, failures, checksum, and estimated import time.
- Credential redaction for source URLs in API responses, logs, import history, diagnostics-facing messages, and dashboard displays.
- Large-playlist safeguards with content-type counts, database-impact estimates, metadata samples without URLs, and explicit confirmation above the configured threshold.
- Non-destructive content classification for Live TV, Movies, Series, and Unknown. Movies and Series are excluded in Milestone 2 because VOD storage is deferred.
- Background worker for queued playlist imports and scheduled refreshes.
- Import history with progress and error reporting.
- Raw channel storage without cleanup, normalization, filtering, duplicate detection, or EPG matching.
- Synthetic demonstration playlist with example-only URLs.

## Local Development

Create a local environment file:

```sh
cp .env.example .env
```

Start the development stack:

```sh
make dev
```

Equivalent direct command:

```sh
docker compose up --build
```

The stack includes PostgreSQL, Redis, the API, dashboard, and source-import worker.

Run migrations:

```sh
make migrate
```

Equivalent direct command:

```sh
docker compose run --rm api alembic -c apps/api/alembic.ini upgrade head
```

Open:

- Dashboard: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Add an M3U source:

1. Sign in to the dashboard.
2. Open `Sources`.
3. Choose `Add Source`.
4. Enter a source name.
5. Select `Remote M3U URL` or `Upload M3U file`.
6. Validate the playlist.
7. Review entry counts, excluded categories, database impact, and any large-import confirmation warning.
8. Choose `Create and import`.

For a safe first import, use `Add demo` on the Sources page. It imports only the built-in synthetic playlist.

Run checks:

```sh
make test
```

Equivalent direct commands:

```sh
docker compose run --rm api ruff check apps/api
docker compose run --rm api mypy apps/api/streamforge_api
docker compose run --rm api pytest apps/api/tests
docker compose run --rm dashboard npm run lint
docker compose run --rm dashboard npm run typecheck
docker compose run --rm dashboard npm run test:run
```

## Security Notice

Use a strong `STREAMFORGE_SECRET_KEY` outside local development. Do not commit `.env`, provider credentials, playlists, recordings, media files, or diagnostic bundles.
