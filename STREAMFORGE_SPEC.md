You are the principal software architect and implementation engineer for a self-hosted television management and Roku playback platform.



Build a production-quality application from this specification. Work methodically, preserve a running application after each milestone, and do not create mock-only interfaces that are disconnected from the backend.



\# Product working name



Use the temporary name \*\*StreamForge\*\* throughout the source code. Keep all branding centralized so the product can be renamed later.



Do not use TiviMate branding, proprietary artwork, copied source code, or pixel-for-pixel interface duplication. This product may reproduce general IPTV-player functionality but must use an original design and implementation.



\# Product goal



Create a private, self-hosted television platform consisting of:



1\. A server deployed on Proxmox VE

2\. A clean browser-based management dashboard

3\. A lightweight Roku playback application

4\. Server-side playlist, guide, recording, timeshift, filtering, and stream-management services



The Roku app must act primarily as a player and television interface. The server is the authoritative source for channels, guide data, favorites, playback history, recordings, configuration, and user profiles.



The software must only play television sources supplied by and authorized for the user. Do not bundle channels, credentials, provider lists, scraping tools, authentication bypasses, DRM circumvention, or copyrighted media.



\# Development strategy



Do not attempt to implement the entire platform in one uncontrolled pass.



First:



1\. Inspect the repository.

2\. Create an architectural plan.

3\. Create `AGENTS.md`.

4\. Create `docs/architecture.md`.

5\. Create `docs/product-requirements.md`.

6\. Create `docs/development-roadmap.md`.

7\. Create `docs/api-contract.md`.

8\. Create `docs/security-model.md`.

9\. Create `docs/proxmox-installation.md`.

10\. Scaffold and implement Milestone 1.

11\. Run formatting, linting, type checking, tests, database migrations, and application health checks.

12\. Report exactly what works, what remains incomplete, and how to run it.



Never silently skip a requirement. Mark intentionally deferred functionality clearly in the roadmap.



\# Primary technology stack



Use a monorepo with the following components.



\## Backend



\* Python 3.13

\* FastAPI

\* Pydantic

\* SQLAlchemy 2

\* Alembic

\* PostgreSQL

\* Redis

\* Celery or an equivalently mature task queue

\* FFmpeg and FFprobe integration through a safe subprocess abstraction

\* Pytest

\* Ruff

\* MyPy or Pyright

\* Structured JSON logging



\## Web dashboard



\* React

\* TypeScript

\* Vite

\* Tailwind CSS

\* A mature accessible component system

\* TanStack Query

\* React Router

\* Zod

\* Vitest

\* Playwright for important browser flows



Do not use Next.js unless there is a documented architectural reason. The dashboard is primarily a client for the FastAPI backend.



\## Roku application



\* BrightScript

\* Roku SceneGraph XML components

\* Roku manifest

\* Server API client

\* HLS playback through Roku-supported video components

\* Local cache only for startup speed and temporary resilience



The Roku application must not contain provider credentials.



\## Deployment



\* Docker Compose as the canonical application deployment

\* Proxmox-friendly installation documentation

\* Deployment inside an unprivileged Debian LXC when possible

\* Optional separate transcoding worker for GPU or hardware acceleration

\* Caddy or NGINX as the reverse proxy

\* Health checks for every long-running service



\# Repository layout



Create a maintainable monorepo approximately following:



/

AGENTS.md

README.md

LICENSE

.env.example

compose.yaml

Makefile

apps/

api/

dashboard/

roku/

services/

worker/

stream-gateway/

packages/

api-contract/

shared-types/

infrastructure/

docker/

proxmox/

reverse-proxy/

docs/

scripts/

tests/



Adjust this layout only when there is a strong documented reason.



\# Core architecture



The application must distinguish between imported provider data and the user’s curated lineup.



Provider source

\-> playlist importer

\-> raw channel records

\-> name normalization

\-> category mapping

\-> duplicate candidate detection

\-> stream health evaluation

\-> quality scoring

\-> filtering rules

\-> curated lineup

\-> Roku and dashboard APIs



Never destructively delete imported source records as part of automatic cleanup. Automatic actions should hide, group, merge, rank, or quarantine entries. Permanent deletion must require an explicit administrative action.



\# Server responsibilities



The server must eventually provide:



\* M3U and M3U8 playlist importing

\* Uploaded playlist support

\* Optional Xtream-compatible account integration for authorized services

\* XMLTV importing and processing

\* Multiple playlist and guide sources

\* Source refresh scheduling

\* Channel normalization

\* Group normalization

\* Channel-logo management

\* Channel-to-EPG mapping

\* Duplicate detection

\* Primary and fallback stream selection

\* Channel-health monitoring

\* Roku-compatible HLS proxying

\* Conditional remuxing

\* Conditional transcoding

\* Recording scheduling

\* Recording execution

\* Series recording rules

\* Recording conflict reporting

\* Timeshift buffering

\* Favorites

\* Profiles

\* Parental controls

\* Playback history

\* Resume positions

\* Roku device pairing

\* Signed playback sessions

\* Backup and restore

\* Application updates

\* Logs and diagnostics



\# Junk-channel filtering engine



Implement a first-class cleanup system rather than a simple text blacklist.



Each imported channel must retain its original source data and receive normalized metadata including:



\* normalized name

\* normalized group

\* inferred country

\* inferred language

\* inferred category

\* claimed quality

\* measured resolution

\* measured frame rate

\* codec information

\* EPG status

\* health status

\* quality score

\* reliability score

\* duplicate-cluster identifier

\* visibility status

\* filtering explanations



Support rules based on:



\* Exact name

\* Name contains

\* Regular expression

\* Source

\* Group

\* Category

\* Country

\* Language

\* Resolution

\* Codec

\* EPG availability

\* Health status

\* Reliability

\* Duplicate availability

\* Last-watched date

\* Explicit allowlist

\* Explicit blocklist



Initial cleanup modes:



\* Light

\* Recommended

\* Aggressive

\* Custom



Filtering must be explainable. Every automatic recommendation or action must include one or more human-readable reasons.



Example:



“Hidden because a healthy 1080p version with matching guide data exists in the same duplicate cluster.”



Allowlist rules must take precedence over automatic cleanup.



\# Duplicate detection



Do not merge channels merely because their names are identical.



Use a staged duplicate-detection approach:



1\. Normalize provider prefixes and suffixes.

2\. Normalize punctuation, spacing, quality labels, country labels, and common aliases.

3\. Compare guide identifiers.

4\. Compare channel names.

5\. Compare group and language.

6\. Compare stream characteristics.

7\. Produce a confidence score.

8\. Automatically merge only above a conservative threshold.

9\. Send uncertain cases to the Cleanup Center.



A duplicate cluster should expose one curated channel with ranked source candidates:



\* Primary

\* Backup 1

\* Backup 2

\* Hidden low-quality source



Preserve the ability to split an incorrectly merged cluster.



\# Stream health and quality scoring



Build the scanner behind an abstraction that can use FFprobe and controlled playback tests.



Capture:



\* HTTP status

\* redirect failures

\* DNS or connection failure

\* time to first media data

\* video codec

\* audio codec

\* resolution

\* frame rate

\* bitrate when measurable

\* timestamp problems

\* probe duration

\* last successful check

\* consecutive failures



Do not scan every provider channel continuously. Use a configurable scheduling strategy and bounded concurrency.



Create a deterministic, documented quality-scoring formula. Keep measured quality and historical reliability as separate concepts.



\# Stream gateway



Expose stable server URLs rather than original provider URLs.



Target endpoints:



\* `/stream/live/{channel\_id}/master.m3u8`

\* `/stream/recording/{recording\_id}/master.m3u8`

\* `/stream/timeshift/{session\_id}/master.m3u8`



Playback policy:



1\. Direct proxy when the source is already compatible and stable.

2\. Remux when the container or timestamps need normalization.

3\. Transcode only when codec compatibility requires it.

4\. Retry approved fallback sources when the primary source fails.

5\. Avoid exposing provider credentials or raw URLs to the Roku.



Prevent command injection. Never concatenate untrusted strings into shell commands. Use argument arrays, validation, timeouts, resource limits, and process cleanup.



\# Recording architecture



The server, not the Roku, performs all recording.



Support the following data model, even when some execution features are deferred:



\* Recording

\* RecordingJob

\* RecordingRule

\* RecordingConflict

\* RecordingFile

\* RetentionPolicy



The Roku and dashboard should be able to request:



\* Record current program

\* Record a future program

\* Record all episodes

\* Record new episodes

\* Add start and end padding

\* Cancel recording

\* Delete recording

\* Resume recorded playback



Store recording media outside the application container using configured mounts.



\# Timeshift architecture



Design timeshift as a server-side rolling HLS buffer.



It must eventually support:



\* Pause live television

\* Resume

\* Rewind

\* Seek within available buffer

\* Jump to live

\* Configurable buffer duration

\* Automatic session expiration

\* Storage quotas and cleanup



Timeshift implementation can be deferred until the stream gateway and live playback are stable, but its interfaces and storage model must be planned now.



\# Web dashboard design



Build a refined, responsive application that feels like a commercial home-media appliance, not a generic administration template.



Visual direction:



\* Sleek dark theme by default

\* Optional light theme

\* Charcoal surfaces

\* Soft elevation

\* Restrained borders

\* Rounded panels

\* Excellent spacing

\* Clear hierarchy

\* Smooth but subtle transitions

\* High readability

\* Responsive phone, tablet, and desktop layouts

\* Accessible focus states

\* WCAG-conscious contrast

\* No excessive gradients

\* No glass effects that reduce readability

\* No arbitrary neon cyberpunk styling



Primary navigation:



\* Dashboard

\* Live TV

\* Channels

\* Cleanup Center

\* Guide

\* Recordings

\* Sources

\* Devices

\* Users and Profiles

\* Storage

\* Diagnostics

\* Settings



\## Dashboard



Display:



\* Overall server status

\* Provider status

\* Active streams

\* Current recordings

\* Upcoming recordings

\* Storage utilization

\* Channel-health summary

\* Guide freshness

\* Connected Roku devices

\* Recent actionable warnings



\## Setup wizard



The first-run wizard must be fully functional and persisted. Include:



1\. Administrator account

2\. Local-only or remote-access operating mode

3\. Recording, timeshift, and temporary storage

4\. Television source

5\. Guide source

6\. Country, language, category, and quality preferences

7\. Cleanup preview

8\. Roku pairing

9\. Final health check



Users must be able to skip optional provider setup and return later.



Validate storage write access and source connectivity before accepting settings.



\## Cleanup Center



Provide queues for:



\* Likely duplicates

\* Dead streams

\* Unstable streams

\* Low-quality duplicates

\* Missing guide data

\* Unknown channels

\* Automatically hidden channels

\* Newly imported channels



Actions:



\* Accept recommendation

\* Keep

\* Hide

\* Always allow

\* Always block

\* Merge

\* Split

\* Set primary

\* Set backup

\* Edit metadata

\* Bulk apply



Always show why a recommendation was made.



\## Channels



Provide:



\* Search

\* Filtering

\* Sorting

\* Virtualized table or grid

\* Bulk actions

\* Channel details

\* Source candidates

\* Guide assignment

\* Logo assignment

\* Group assignment

\* Visibility controls

\* Quality and health information



Do not attempt to render thousands of rows directly without virtualization or pagination.



\## Diagnostics



Show plain-language errors first, with expandable technical data.



Provide correlation IDs so UI errors can be matched to backend logs.



\# Authentication and security



Support a secure local administrator account.



Requirements:



\* Argon2id password hashing

\* Secure session cookies for the dashboard

\* CSRF protection where relevant

\* Rate limiting

\* Audit logging for security-sensitive changes

\* Device-specific Roku tokens

\* Revocable device sessions

\* Short-lived signed playback authorization

\* Encrypted provider secrets at rest

\* No secrets in logs

\* No credentials in frontend bundles

\* Strict input validation

\* Safe URL handling

\* Server-side request forgery protections for administrator-supplied URLs

\* Private-network destination policy that is configurable for home-lab use

\* CORS restricted by configuration

\* Secure production defaults



Do not build a custom cryptographic algorithm.



\# Roku device pairing



Implement a device-code flow.



The Roku requests a pairing code from the server. The server returns:



\* short human-readable code

\* device request identifier

\* expiration time

\* polling interval



The administrator enters the code in the dashboard and assigns:



\* device name

\* room

\* profile

\* permissions



After approval, the Roku receives a revocable device credential.



Codes must expire and be single-use.



\# Roku interface



Create an original television-first interface.



Primary sections:



\* Home

\* Live TV

\* Guide

\* Recordings

\* Search

\* Settings



Live TV must eventually include:



\* Channel groups

\* Channel list

\* Current and next program

\* Full-screen playback

\* Mini guide

\* Channel recall

\* Favorites

\* Recently watched

\* Stream-error recovery

\* Server status feedback



Remote behavior:



\* OK: tune or show controls depending on context

\* Back: dismiss layer, then return

\* Left: channel groups or previous navigation layer

\* Right: program information or future guide

\* Up and Down: channel navigation or guide movement

\* Replay: configurable recent-channel action

\* Options: channel actions and diagnostics



Keep navigation predictable and avoid trapping focus.



\# API requirements



Use `/api/v1`.



Initial API areas:



\* `/health`

\* `/auth`

\* `/setup`

\* `/sources`

\* `/playlists`

\* `/epg-sources`

\* `/channels`

\* `/channel-groups`

\* `/cleanup`

\* `/guide`

\* `/recordings`

\* `/recording-rules`

\* `/devices`

\* `/pairing`

\* `/profiles`

\* `/favorites`

\* `/playback`

\* `/storage`

\* `/diagnostics`

\* `/settings`



Generate and maintain an OpenAPI schema.



Create typed dashboard clients from the API schema or otherwise enforce compile-time contract consistency.



Use cursor pagination or another scalable approach for large channel datasets.



\# Database requirements



Create explicit database models and migrations for at least:



\* User

\* Session

\* Profile

\* Device

\* DevicePairingCode

\* Source

\* PlaylistImport

\* RawChannel

\* CuratedChannel

\* ChannelSourceCandidate

\* ChannelGroup

\* ChannelAlias

\* EpgSource

\* EpgChannel

\* Program

\* ChannelEpgMapping

\* FilterRule

\* FilterDecision

\* DuplicateCluster

\* StreamHealthResult

\* Favorite

\* PlaybackProgress

\* Recording

\* RecordingRule

\* RecordingJob

\* RecordingConflict

\* StorageLocation

\* SystemSetting

\* AuditEvent



Use timezone-aware UTC timestamps internally.



Add appropriate indexes for channel search, program time ranges, source relationships, health status, filtering state, and recording schedules.



\# Background jobs



Plan and implement bounded jobs for:



\* Playlist import

\* EPG import

\* Channel normalization

\* Duplicate analysis

\* Filtering evaluation

\* Stream probing

\* Recording scheduling

\* Recording execution

\* Retention cleanup

\* Timeshift cleanup

\* Backup creation



Jobs must be idempotent where practical.



Record job status, progress, retry count, start time, completion time, and failure reason.



\# Observability



Implement:



\* Structured logs

\* Request IDs

\* Job IDs

\* Health endpoints

\* Readiness checks

\* Service version reporting

\* FFmpeg process tracking

\* Basic metrics suitable for future Prometheus export



Never expose secrets in diagnostic bundles.



\# Backup and restore



Design backups for:



\* Configuration

\* Database

\* Channel mappings

\* Filter rules

\* Profiles

\* Device registrations

\* Recording metadata

\* Custom logos



Media recordings should be optional.



Before restoration, validate archive format and version compatibility.



\# Installation and operation



Provide:



\* `.env.example`

\* Docker Compose configuration

\* Database migrations

\* Seed or demonstration data that contains no copyrighted provider content

\* Health-check script

\* Backup script

\* Restore script

\* Proxmox LXC installation guide

\* Reverse-proxy guide

\* Update guide

\* Rollback guide

\* Troubleshooting guide



Do not create an unsafe `curl | bash` installer during the first milestone.



Eventually, an installer may be created, but it must:



\* display what it will do

\* support a dry-run mode

\* avoid embedding secrets

\* avoid modifying the Proxmox host unnecessarily

\* create backups before destructive changes

\* fail safely



\# Engineering quality requirements



\* Use strict TypeScript.

\* Use typed Python.

\* Keep business logic out of route handlers and React components.

\* Use dependency injection or clear service boundaries.

\* Avoid giant files.

\* Avoid placeholder implementations presented as complete.

\* Do not swallow exceptions.

\* Use domain-specific exceptions and user-safe messages.

\* Add tests for critical behavior.

\* Add database migrations for every schema change.

\* Use secure defaults.

\* Document non-obvious decisions.

\* Keep generated files out of version control unless necessary.

\* Add `.gitignore`, editor configuration, and formatting configuration.

\* Do not commit `.env`, credentials, media, recordings, or provider playlists.



\# Test requirements



At minimum, eventually include tests for:



\* M3U parsing

\* XMLTV parsing

\* Name normalization

\* Filtering precedence

\* Allowlist override

\* Duplicate clustering

\* Quality scoring

\* Source refresh behavior

\* Pairing-code expiration

\* Pairing-code single use

\* Authentication

\* Signed playback authorization

\* Recording scheduling

\* Guide time-range queries

\* Storage validation

\* API authorization

\* SSRF protections



Use synthetic fixtures only.



\# Milestone plan



\## Milestone 1 — Runnable foundation



Implement now:



\* Monorepo structure

\* Docker Compose

\* PostgreSQL

\* Redis

\* FastAPI application

\* React dashboard

\* Database migrations

\* Health and readiness endpoints

\* Administrator creation

\* Authentication

\* Persisted first-run state

\* First-run wizard shell with functional account and installation-mode steps

\* Dashboard shell with functional server-health cards

\* Structured logging

\* Basic automated tests

\* Complete local-development instructions



Acceptance criteria:



\* One documented command starts the development stack.

\* Database migrations run successfully.

\* An administrator can be created.

\* An administrator can sign in and sign out.

\* First-run state persists.

\* Dashboard health information comes from live backend endpoints.

\* Restarting containers does not lose database state.

\* Backend tests pass.

\* Frontend type checking and tests pass.

\* No critical security shortcuts are left undocumented.



\## Milestone 2 — Sources and playlist ingestion



Later implement:



\* M3U URL source

\* Uploaded M3U source

\* Asynchronous import job

\* Raw channel storage

\* Import history

\* Source refresh

\* Source status UI

\* Safe URL validation

\* Synthetic demonstration playlist



\## Milestone 3 — Channel normalization and cleanup



Later implement:



\* Normalization engine

\* Filter-rule model

\* Light, Recommended, Aggressive, and Custom cleanup profiles

\* Explainable filter decisions

\* Channel manager

\* Cleanup Center

\* Duplicate candidate detection

\* Merge and split operations



\## Milestone 4 — XMLTV and guide



Later implement:



\* XMLTV ingestion

\* Program storage

\* Guide mappings

\* Suggested mappings

\* Guide API

\* Dashboard guide view



\## Milestone 5 — Stream health and playback gateway



Later implement:



\* Safe FFprobe abstraction

\* Health checks

\* Quality scoring

\* Stable live-stream URLs

\* Direct proxy and remux decisions

\* Signed playback sessions

\* Fallback source selection



\## Milestone 6 — Roku MVP



Later implement:



\* Device pairing

\* Roku navigation shell

\* Channel groups

\* Channel list

\* Guide

\* HLS playback

\* Favorites

\* Recent channels

\* Error recovery



\## Milestone 7 — Recording



Later implement:



\* Recording scheduler

\* FFmpeg recording worker

\* Recording library

\* Guide-based recording

\* Padding

\* Retention rules

\* Roku recording playback



\## Milestone 8 — Timeshift and advanced capabilities



Later implement:



\* Rolling timeshift

\* Series recording

\* Advanced conflict management

\* Hardware-transcoding profiles

\* Multi-user profiles

\* Backup and restore

\* Update and rollback workflow



\# Current task



Implement \*\*Milestone 1 only\*\*.



Before editing code:



1\. State the proposed architecture.

2\. State assumptions.

3\. Identify important risks.

4\. Show the intended repository tree.

5\. Then create the files and implementation.



After implementation:



1\. Run all available tests and checks.

2\. Fix failures rather than merely describing them.

3\. Review the diff for incomplete placeholder behavior.

4\. Review authentication and secret handling.

5\. Update documentation.

6\. Provide exact startup commands.

7\. Provide the default local URLs.

8\. List all deferred items.

9\. Suggest the exact next Codex task for Milestone 2.



Do not stop after scaffolding. Deliver a working, tested Milestone 1.



