# StreamForge Architecture

`STREAMFORGE_SPEC.md` is the authoritative specification. This document records the implemented architecture through Milestone 2 and the boundaries for later milestones.

## System Shape

StreamForge is a self-hosted television management and playback platform composed of:

- `apps/api`: FastAPI backend, database models, migrations, authentication, setup state, health, readiness, source management, playlist ingestion, and structured logging.
- `apps/dashboard`: React dashboard for setup, authentication, server health, source management, and import history.
- `apps/roku`: Roku application placeholder tree only during Milestone 1.
- `services/worker`: background worker boundary for asynchronous playlist imports and scheduled refreshes.
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

Docker Compose is the canonical local and home-lab deployment path. It starts PostgreSQL, Redis, the API, the dashboard, and the playlist-import worker with persistent database, Redis, and uploaded-source volumes. Proxmox installation documentation targets an unprivileged Debian LXC when possible.

## Milestone 2 Source Ingestion

Milestone 2 adds television source management without cleanup, duplicate detection, guide matching, playback, recording, timeshift, or Roku behavior.

The source ingestion flow is:

Provider source -> safe validation -> source record -> playlist import job -> background worker -> raw channel records -> source status and import history.

Key boundaries:

- Remote M3U URLs are validated for supported protocols and private-network safety before fetch.
- Uploaded M3U files are stored under the configured upload directory with sanitized generated names.
- Sensitive source configuration, including remote URLs and upload paths, is encrypted before persistence and never returned to the dashboard.
<<<<<<< HEAD
- `PlaylistImportJob` records queued/running/succeeded/failed progress for the worker.
- `PlaylistImport` records start time, completion time, duration, imported channel count, group count, warnings, failures, checksum, and source version.
- `RawChannel` stores provider data exactly as imported for each successful import row, including original name, original group, original URL, tvg metadata, raw EXTINF line, raw attributes, and import line number.
=======
- URL redaction is centralized and applied to API responses, status messages, import failures, audit details, and structured logs.
- Large remote and uploaded playlists are copied to bounded server-side files and parsed line-by-line rather than loaded into memory.
- Validation reports total entries, selected entries, excluded entries, content-type counts, sampled metadata without stream URLs, database-row estimates, and large-import confirmation requirements.
- Content classification is non-destructive and limited to Live TV, Movie, Series Episode, and Unknown heuristics. Movies and Series are counted but excluded because Milestone 2 has no safe VOD storage model.
- `PlaylistImportJob` records queued/running/succeeded/failed progress for the worker.
- `PlaylistImport` records start time, completion time, duration, imported channel count, group count, warnings, failures, checksum, and source version.
- `RawChannel` stores provider data exactly as imported for each successful import row, including original name, original group, original URL, tvg metadata, raw EXTINF line, raw attributes, and import line number.
- Repeat imports replace the previous raw rows for the source inside one transaction to prevent uncontrolled raw-row growth while keeping failure rollback consistent.
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
- The worker polls queued jobs and due refreshes. API source creation returns immediately after queueing an import job.

Scheduled refresh uses each source's `refresh_interval_minutes` and `next_refresh_at`. The worker avoids queueing a scheduled refresh when another queued or running import already exists for that source.

## Milestone 2 Risks and Guardrails

- Provider URLs can target unsafe networks, so remote fetches reject unsupported protocols, local file URLs, invalid paths, and private/reserved destinations by default.
- Provider URLs may contain credentials, so persisted source secrets are encrypted and API responses return only redacted display locations.
<<<<<<< HEAD
- Playlists may be huge or malformed, so validation enforces a byte limit and records human-readable warnings and failures instead of blocking the API thread.
=======
- Playlists may be huge or malformed, so validation enforces byte and entry-count thresholds, requires administrator confirmation above the configured threshold, and records human-readable warnings and failures.
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
- Import jobs can stall if the worker is not running, so the dashboard exposes queued/running job progress and Docker Compose starts a dedicated `worker` service.
- Uploaded playlists can be path-confusion risks, so files are stored with generated sanitized names and reloaded only from the configured upload directory.

## Deferred Architecture

The following are planned but not implemented through Milestone 2:

- Channel normalization, duplicate detection, cleanup, and quality scoring.
- XMLTV ingestion and guide matching.
- FFprobe and FFmpeg process integration.
- Stream gateway, signed playback sessions, live HLS proxying, remuxing, and transcoding.
- Roku device pairing and Roku playback UI.
- Recording, timeshift, backup, restore, update, and rollback workflows.
