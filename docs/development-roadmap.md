# StreamForge Development Roadmap

## Milestone 1 - Runnable Foundation

Status: implemented in repository; full Docker and frontend validation require Docker and Node package installation.

Deliver:

- Monorepo structure.
- Docker Compose development stack.
- PostgreSQL and Redis services.
- FastAPI app with health, readiness, auth, setup state, migrations, and structured logs.
- React dashboard with first-run wizard, auth, and live health cards.
- Basic backend and frontend tests.
- Local development documentation.

Implemented notes:

- Administrator bootstrap is closed after the first admin exists or setup is complete.
- Authentication uses Argon2id password hashing and server-side sessions referenced by signed HTTP-only cookies.
- Setup completion for Milestone 1 means the administrator account and installation-mode steps are persisted.
- Dashboard health cards read from live backend endpoints.

Deferred from Milestone 1:

- Real provider source setup.
- Playlist upload or URL import.
- EPG import.
- Cleanup recommendations.
- Roku pairing.
- Stream playback.
- Recording and timeshift execution.

## Milestone 2 - Sources and Playlist Ingestion

Status: implemented in repository; full Docker and frontend validation require Docker and Node package installation.

Delivered:

- M3U URL source.
- Uploaded M3U source.
- Asynchronous import job.
- Raw channel storage.
- Import history.
- Source refresh.
- Source status UI.
- Safe URL validation.
- Synthetic demonstration playlist.
- Background worker polling integration.
- Progress and error reporting.

Implemented notes:

- Imports store raw channel records first. Milestone 3 normalization and cleanup run as a separate job so raw provider evidence remains preserved.
- The worker processes queued jobs outside the API process.
- Remote source URLs are encrypted at rest and redacted in dashboard/API responses.
- Uploaded files are saved under `STREAMFORGE_SOURCE_UPLOAD_DIR` and imported by the worker.

## Milestone 3 - Channel Normalization and Cleanup

Status: implemented in repository; full Docker and frontend validation require Docker and Node package installation.

Delivered:

- Normalization engine.
- Normalization job tracking.
- Standard channel groups.
- Filter-rule and filter-decision models.
- Light, Recommended, Aggressive, and Custom cleanup profiles.
- Explainable filter decisions.
- Channels page.
- Cleanup Center.
- Duplicate candidate detection.
- Merge and split operations.
- Reversible protect-from-auto-merge and allowlist/blocklist overrides.
- Curated channel and source-candidate generation.
- Cursor-paginated channel API.

Implemented notes:

- Automatic cleanup hides, groups, ranks, and clusters rows but does not permanently delete raw imported provider records.
- Identical names alone are not enough for duplicate merging; compatible metadata or strong identifiers are required.
- The worker processes queued normalization jobs after import jobs.
- Dashboard channel and candidate views show checksums and metadata only, never raw stream URLs.
- XMLTV, playback, Roku, recording, timeshift, FFmpeg/FFprobe probing, and guide mapping remain deferred.

## Milestone 4 - XMLTV and Guide

Status: deferred.

Planned:

- XMLTV ingestion.
- Program storage.
- Guide mappings.
- Suggested mappings.
- Guide API.
- Dashboard guide view.

## Milestone 5 - Stream Health and Playback Gateway

Status: deferred.

Planned:

- Safe FFprobe abstraction.
- Health checks.
- Quality scoring.
- Stable live-stream URLs.
- Direct proxy and remux decisions.
- Signed playback sessions.
- Fallback source selection.

## Milestone 6 - Roku MVP

Status: deferred.

Planned:

- Device pairing.
- Roku navigation shell.
- Channel groups.
- Channel list.
- Guide.
- HLS playback.
- Favorites.
- Recent channels.
- Error recovery.

## Milestone 7 - Recording

Status: deferred.

Planned:

- Recording scheduler.
- FFmpeg recording worker.
- Recording library.
- Guide-based recording.
- Padding.
- Retention rules.
- Roku recording playback.

## Milestone 8 - Timeshift and Advanced Capabilities

Status: deferred.

Planned:

- Rolling timeshift.
- Series recording.
- Advanced conflict management.
- Hardware-transcoding profiles.
- Multi-user profiles.
- Backup and restore.
- Update and rollback workflow.
