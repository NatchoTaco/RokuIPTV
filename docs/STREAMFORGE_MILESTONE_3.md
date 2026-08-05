# StreamForge Milestone 3 Specification

Read `AGENTS.md` and every document under `docs/` before making changes.

Review the current repository, Git history, database models, APIs, dashboard, and completed Milestone 1 and Milestone 2 behavior.

Milestone 2 is deployed and working with a real authorized provider playlist.

## Observed real-world source characteristics

- Approximately 940,960 total playlist entries
- Approximately 15,852 selected Live TV + Unknown entries
- Only about 808 entries were classified explicitly as Live TV
- Approximately 15,044 likely live channels were classified as Unknown
- The provider supplied no usable `group-title` metadata
- Movies and series were successfully excluded
- Credentials are now redacted
- Import completed with nonfatal warnings

## Scope

Implement **Milestone 3 only**.

Milestone 3 goal:

Create the channel normalization, organization, duplicate-analysis, filtering, and curated-lineup system while preserving all imported raw records.

Do not begin XMLTV/EPG, playback, Roku, recording, or timeshift work.

## Core data model

Implement and migrate the models needed for:

- `CuratedChannel`
- `ChannelSourceCandidate`
- `ChannelGroup`
- `ChannelAlias`
- `FilterRule`
- `FilterDecision`
- `DuplicateCluster`
- `NormalizationJob` or equivalent job tracking
- User overrides and protected allowlist decisions

`RawChannel` must remain immutable source evidence except for import lifecycle management. Never destructively modify or delete raw provider data during automatic cleanup.

## Normalization

Create a deterministic and tested normalization pipeline that:

- Removes common provider prefixes and suffixes
- Normalizes whitespace and punctuation
- Separates quality labels such as SD, HD, FHD, UHD, 4K, 50 FPS, and 60 FPS
- Recognizes country and region prefixes
- Preserves the original provider name
- Produces a clean display name
- Infers language, country, category, and likely content type
- Extracts meaningful metadata from names when `group-title` is absent
- Handles Unicode correctly
- Records a human-readable explanation for each inferred value

Do not overwrite original imported fields.

## Group inference

Because the real provider reports zero usable groups, infer sensible groups from channel names and metadata.

Initial standard groups should include:

- Local
- News
- Sports
- Entertainment
- Movies
- Kids
- Documentary
- Lifestyle
- Music
- Weather
- International
- Events
- Religious
- Shopping
- Adult
- Other

Group inference must be rule-driven, explainable, editable, and reversible.

## Duplicate analysis

Implement conservative duplicate candidate detection using:

- Normalized names
- `tvg-id` when present
- Country and language
- Quality labels
- Network or affiliate identity
- Stream metadata available from import
- Similarity scoring

Do not merge merely because two names are identical.

Create duplicate clusters with:

- Confidence score
- Explanation
- Suggested primary source
- Backup candidates
- Hidden low-quality candidates
- Ability to merge manually
- Ability to split an incorrect cluster
- Ability to protect a channel from future automatic merging
- Ability to remove manual protection without deleting, hiding, merging, or altering the channel

Only automatically merge at a conservative configurable threshold. Uncertain cases must appear in the Cleanup Center.

## Filtering engine

Implement explainable rules for:

- Exact name
- Name contains
- Regular expression
- Source
- Inferred group
- Country
- Language
- Resolution or claimed quality
- Missing name
- Missing metadata
- Duplicate availability
- Adult content
- Shopping
- Religious
- Test and backup channels
- 24/7 loop channels
- Foreign-language content
- Allowlist
- Blocklist

Support cleanup profiles:

- Light
- Recommended
- Aggressive
- Custom

Allowlist decisions must override automatic filtering.

Automatic cleanup must hide, quarantine, rank, or group entries. It must not permanently delete imported data.

## Dashboard

Activate and implement:

1. Channels page
2. Cleanup Center

### Channels page

Support:

- Search
- Pagination or virtualization
- Filtering
- Sorting
- Original and normalized names
- Inferred group
- Source
- Visibility
- Duplicate status
- Quality label
- Bulk actions
- Manual rename
- Manual group assignment
- Always allow
- Always hide
- Protect and unprotect
- Bulk unprotect protected channels
- Filter to protected channels
- View source candidates

### Cleanup Center

Show queues for:

- Likely duplicates
- Missing or malformed names
- Test and backup channels
- Low-quality duplicates
- Unclassified channels
- Suspected adult content
- Shopping and religious channels
- Foreign-language channels
- Newly imported channels

The Cleanup Center must allow protected duplicate clusters to be unprotected and must include a confirmed administrative action to clear all manual protection overrides while preserving explicit Allow and Hide decisions.
- Automatically hidden entries

Every recommendation must show a plain-language reason.

Provide Preview and Apply behavior so an administrator can see the effect of a cleanup profile before changing the curated lineup.

## Large dataset requirements

The implementation must remain responsive with at least 20,000 selected raw entries.

Requirements:

- Bounded background jobs
- Batched database operations
- Appropriate indexes
- Cursor pagination or another scalable query design
- No loading the entire lineup into the browser
- Progress and cancellation reporting
- Idempotent reruns
- No uncontrolled duplication on repeated normalization
- Safe recovery after a failed job

## Testing

Add synthetic tests covering:

- Provider prefixes
- Missing `group-title`
- Unknown entries that are actually live channels
- Quality suffixes
- Country prefixes
- Unicode names
- Duplicate candidates
- False duplicate avoidance
- Allowlist precedence
- Filter explanations
- Idempotent normalization
- Repeated source refresh
- Large generated datasets

Run:

- Repository-wide conflict-marker search
- Python compile checks
- Ruff
- MyPy
- Pytest
- Frontend tests
- TypeScript checks
- Production dashboard build
- Alembic migration validation
- Docker Compose validation
- API and worker startup tests

Do not include or use the real provider playlist or credentials in fixtures, tests, source code, logs, or documentation.

## Required completion report

At completion, report:

- Database migrations added
- Models added
- APIs added
- Normalization behavior
- Group-inference behavior
- Duplicate-scoring behavior
- Filtering precedence
- Dashboard flows
- Performance safeguards
- Every validation command and result
- Remaining limitations

Do not begin Milestone 4.
