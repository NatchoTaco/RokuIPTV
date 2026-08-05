# StreamForge Product Requirements

## Product Goal

StreamForge is a private, self-hosted television platform with a server, browser dashboard, Roku playback app, and server-side services for playlist, guide, recording, timeshift, filtering, and stream management.

The server is the authoritative source for channels, guide data, favorites, playback history, recordings, configuration, user profiles, and device state. Roku clients act primarily as playback and television interfaces.

## Non-Negotiable Constraints

- Use only user-supplied and authorized television sources.
- Do not bundle channels, credentials, provider lists, scraping tools, authentication bypasses, DRM circumvention, or copyrighted media.
- Do not use TiviMate branding, proprietary artwork, copied source code, or pixel-for-pixel interface duplication.
- Preserve imported provider records. Automatic cleanup may hide, rank, merge, group, or quarantine records, but permanent deletion requires explicit administrative action.
- Keep automatic cleanup explainable and allowlist rules higher priority than automatic cleanup.

## Milestone 1 Requirements

Milestone 1 must deliver a runnable foundation:

- Monorepo structure.
- Docker Compose.
- PostgreSQL and Redis.
- FastAPI application.
- React dashboard.
- Database migrations.
- Health and readiness endpoints.
- Administrator creation.
- Authentication.
- Persisted first-run state.
- First-run wizard shell with functional account and installation-mode steps.
- Dashboard shell with functional server-health cards.
- Structured logging.
- Basic automated tests.
- Complete local-development instructions.

## Milestone 1 Acceptance Criteria

- One documented command starts the development stack.
- Database migrations run successfully.
- An administrator can be created.
- An administrator can sign in and sign out.
- First-run state persists.
- Dashboard health information comes from live backend endpoints.
- Restarting containers does not lose database state.
- Backend tests pass.
- Frontend type checking and tests pass.
- No critical security shortcuts are left undocumented.

## Milestone 2 Requirements

Milestone 2 delivers source management and playlist ingestion:

- Fully functional dashboard Sources page.
- Add Source wizard for source name, remote/upload choice, and source validation.
- Remote M3U URL source support.
- Uploaded M3U file source support.
- Safe URL validation with unsupported protocol and private-network rejection by default.
- Asynchronous playlist import jobs processed by the background worker.
- Playlist import history with start time, completion time, duration, channels, groups, warnings, failures, checksum, and source version.
- Raw channel storage preserving provider metadata exactly as imported.
- Playlist refresh scheduling.
- Source status monitoring and human-readable error reporting.
- Synthetic demonstration playlist containing only example, non-provider URLs.
- Unit tests for parser, URL safety, and source import behavior.

Milestone 2 explicitly does not perform cleanup, duplicate detection, normalization, filtering, EPG matching, playback, recording, timeshift, or Roku work.

## Deferred Product Areas

The following are deliberately deferred beyond Milestone 2:

- Cleanup Center, filter rules, duplicate detection, and channel manager.
- XMLTV guide ingestion and mapping.
- Stream probing, quality scoring, and playback gateway.
- Roku MVP.
- Recording and recording playback.
- Timeshift and advanced platform operations.
