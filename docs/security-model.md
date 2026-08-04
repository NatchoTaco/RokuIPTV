# StreamForge Security Model

## Milestone 1 Security Scope

Milestone 1 implements secure local administrator authentication and session management for the dashboard.

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

## Configuration

Production deployments must provide a strong `STREAMFORGE_SECRET_KEY`. Development has a default key only for local use. CORS origins are restricted by configuration.

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
- Encrypted provider secrets at rest.
- SSRF protection for administrator-supplied provider URLs.
- Private-network destination policies.
- Diagnostic bundle redaction.
