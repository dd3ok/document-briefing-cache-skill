# Changelog

## Unreleased

### Changed

- Made Briefprint explicit-use in agent metadata so ordinary one-off summaries do not automatically invoke the cached briefing skill.
- Replaced broad natural-language trigger examples with `$briefprint` invocation examples.
- Added `disable-model-invocation: true` to the installable skill metadata for hosts that support manual-only skill invocation.
- Documented the boundary between the static agent skill bundle and Briefprint runtime caches under `--cache-dir`.

## 0.4.0 - 2026-07-05

### Added

- Added the `briefprint` installable skill bundle under `skills/briefprint`.
- Added cache explanation output for document cache and rendered-output cache behavior.
- Added the incident lifecycle example and README benchmark shape.
- Added `--sensitive` as a safe default alias for ephemeral cache, no output cache, PII redaction, and delete-on-exit behavior.
- Added secret redaction support for cache and summarizer boundaries.
- Added Korean README coverage in `README.ko.md`.

### Changed

- Rebranded the agent-facing skill surface to Briefprint while retaining the Python package name `document-briefing-cache`.
- Kept installable agent skill files separate from repository runtime, tests, docs, examples, and packaging files.
- Tightened skill metadata, routing boundaries, and bundle validation.
- Bumped runtime and skill metadata to `0.4.0`; cache keys include the skill version, so prior `0.3.x` document-summary cache entries are treated as misses after upgrade.

### Security

- Documented that HMAC signing is tamper detection only and does not encrypt plaintext cache files.
- Documented sensitive-document defaults and redaction limitations.
