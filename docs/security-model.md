# StreamForge Security Model

## Implemented Security Scope

Milestone 1 implements secure local administrator authentication and session management for the dashboard. Milestone 2 adds administrator-only source management, source URL validation, encrypted source secrets, and redacted source responses.

Implemented controls:

- Argon2id password hashing.
- Server-side session records.
- Signed HTTP-only dashboard session cookies.
- Configurable secure cookie flag.
- SameSite cookie policy.
- Request IDs in responses and logs.
- Structured JSON logs.
- No secrets returned by public settings or diagnostics endpoints.
- Bootstrap administrator endpoint blocked after setup completion or after an administrator exists.
- Source management APIs require an authenticated administrator.
- Remote source URLs are encrypted at rest using a mature authenticated-encryption library and a key derived from `STREAMFORGE_SECRET_KEY`.
- Source URLs are redacted before returning to the dashboard.
- User info and sensitive query parameters such as `username`, `password`, `token`, `auth`, and `key` are centrally redacted from API responses, logs, audit details, exceptions, import history, diagnostics-facing messages, and dashboard display text.
- Unencrypted HTTP sources are allowed for authorized home-lab/provider cases but produce a warning during validation.
- Unsupported protocols, local file URLs, invalid URL paths, and private/reserved network destinations are rejected by default for remote playlist fetches.
- Uploaded playlists are stored with generated sanitized names under `STREAMFORGE_SOURCE_UPLOAD_DIR`.

## Configuration

Production deployments must provide a strong `STREAMFORGE_SECRET_KEY`. Development has a default key only for local use. CORS origins are restricted by configuration.

`STREAMFORGE_ALLOW_PRIVATE_SOURCE_URLS=false` is the secure default. Home-lab operators can set it to `true` only when they intentionally need to import from trusted private-network playlist servers.

## Secret Handling

Secrets must not be committed. Sensitive values belong in environment variables or a future secret store. Logs must not include passwords, session tokens, provider credentials, raw provider URLs containing credentials, device credentials, signed playback tokens, or encryption keys.

## Passwords

Passwords are hashed with Argon2id through a mature password-hashing library. Plaintext passwords are accepted only at the authentication boundary and are never persisted.

## Sessions

Dashboard sessions are stored server-side and referenced by a signed cookie. Sign-out revokes the current session. Expired sessions are rejected.

## Deferred Security Controls

The following controls are required by the specification but deferred until the related features exist:

- CSRF protection for unsafe browser requests.
- Rate limiting.
- Audit logging for all security-sensitive changes beyond administrator bootstrap.
- Device-specific Roku credentials.
- Revocable device sessions.
- Short-lived signed playback authorization.
- Expanded source allowlists and per-source network policy overrides.
- Diagnostic bundle redaction.
