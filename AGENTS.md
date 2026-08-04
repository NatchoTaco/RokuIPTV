# StreamForge Agent Guide

This repository follows `STREAMFORGE_SPEC.md` as the authoritative product and engineering specification.

## Scope Control

- Implement one milestone at a time.
- Do not begin Milestone 2 work until Milestone 1 has been delivered and accepted.
- Mark intentionally deferred features in `docs/development-roadmap.md`.
- Keep the working name `StreamForge` centralized so it can be renamed later.

## Security Rules

- Do not commit `.env`, provider playlists, credentials, recordings, media, database dumps, or generated diagnostic bundles.
- Do not bundle channels, provider credentials, copyrighted media, scraping tools, DRM bypasses, or authentication bypasses.
- Use secure defaults for authentication, cookies, CORS, password hashing, logging, and secrets.
- Never log passwords, provider URLs containing credentials, session tokens, device credentials, or signed playback tokens.
- Avoid custom cryptography. Use mature libraries for password hashing and token signing.

## Backend Guidelines

- Use Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Redis, pytest, ruff, and mypy.
- Keep business logic out of route handlers.
- Put database access behind repository or service boundaries.
- Use timezone-aware UTC timestamps internally.
- Add Alembic migrations for schema changes.
- Use structured JSON logs and request IDs.
- Model future platform concepts explicitly when required, but do not expose unfinished behavior as complete.

## Frontend Guidelines

- Use React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Zod, Vitest, and strict TypeScript.
- Keep business logic out of React components.
- Use accessible controls and visible focus states.
- Use a refined dark theme by default with restrained borders, clear hierarchy, and readable contrast.
- Dashboard data must come from live backend endpoints, not mock-only interfaces.

## Repo Hygiene

- Prefer small files with clear ownership.
- Keep generated files out of version control unless necessary.
- Use synthetic fixtures only.
- Run available formatting, linting, type checking, tests, migrations, and health checks before handoff.
