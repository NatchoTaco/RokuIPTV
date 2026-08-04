# StreamForge Architecture

`STREAMFORGE_SPEC.md` is the authoritative specification. This document records the planned architecture for Milestone 1 and the boundaries for later milestones.

## System Shape

StreamForge is a self-hosted television management and playback platform composed of:

- `apps/api`: FastAPI backend, database models, migrations, authentication, setup state, health, readiness, and structured logging.
- `apps/dashboard`: React dashboard for setup, authentication, and server health.
- `apps/roku`: Roku application placeholder tree only during Milestone 1.
- `services/worker`: background worker placeholder tree only during Milestone 1.
- `services/stream-gateway`: stream gateway placeholder tree only during Milestone 1.
- `packages/api-contract`: generated or checked API schema artifacts.
- `packages/shared-types`: future shared contracts and generated types.
- `infrastructure`: Docker, Proxmox, and reverse-proxy configuration.
- `docs`: product and operational documentation.
- `scripts`: health and operational helper scripts.

## Milestone 1 Backend

The API owns all authoritative data and exposes `/api/v1` endpoints. Route handlers remain thin and delegate to services. SQLAlchemy models provide explicit persistence for users, sessions, setup state, audit events, system settings, and the future domain tables required by the specification.

Milestone 1 implements:

- Application factory and typed settings.
- PostgreSQL-backed persistence.
- Alembic migrations.
- Argon2id password hashing.
- Secure signed dashboard sessions stored server-side.
- First administrator creation before setup completion.
- Sign in, sign out, and current-user endpoints.
- Persisted setup state for first-run wizard progress.
- Health and readiness endpoints.
- Structured JSON request logging.

## Milestone 1 Dashboard

The dashboard is a client for the API. It does not present mocked backend state as real functionality.

Milestone 1 implements:

- First-run wizard shell.
- Functional administrator account step.
- Functional installation-mode step.
- Authenticated dashboard shell.
- Server-health cards backed by live API calls.
- Sign-in and sign-out flows.
- Typed API client functions and Zod validation.

## Deployment

Docker Compose is the canonical local and home-lab deployment path. It starts PostgreSQL, Redis, the API, and the dashboard with persistent database and Redis volumes. Proxmox installation documentation targets an unprivileged Debian LXC when possible.

## Deferred Architecture

The following are planned but not implemented in Milestone 1:

- Playlist and XMLTV ingestion.
- Channel normalization, duplicate detection, cleanup, and quality scoring.
- FFprobe and FFmpeg process integration.
- Stream gateway, signed playback sessions, live HLS proxying, remuxing, and transcoding.
- Roku device pairing and Roku playback UI.
- Recording, timeshift, backup, restore, update, and rollback workflows.
