# StreamForge

StreamForge is a private, self-hosted television management and Roku playback platform. The current implementation is limited to Milestone 1 from `STREAMFORGE_SPEC.md`.

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
