# Dimension: breaking changes

Goal: find every way this change can break something that already runs — other clients,
other services, existing data, running deployments. Analyze all integration surfaces; do
not stop after the first finding.

## Integration surfaces

**HTTP API contract (FastAPI ↔ React and other consumers)**
- Endpoint removed or renamed; path/method changed; prefix/version changed.
- Response field removed, renamed, type changed, nullable → non-null or the reverse.
- Request: new required field, stricter validation (`extra="forbid"` added, shorter
  `max_length`, new enum restriction) without updating all clients.
- Status codes or error format changed (`detail` shape) — the frontend parses them.
- Pagination, sorting or default values changed.
- Check the frontend: generated API client/types, query functions and forms that use
  the changed endpoint — are they updated **in the same change**?

**Database**
- Column/table dropped or renamed while the old code version still runs (rolling
  deploy) → needs expand/contract over two releases.
- `NOT NULL` without default/backfill on a filled table; new unique constraint on data
  with duplicates.
- Long-locking migrations on large tables (adding an index without `CONCURRENTLY`,
  rewriting a column type).
- Migration not reversible or `downgrade` wrong/missing.
- RLS policies changed — existing queries may suddenly return nothing.

**Configuration and environment**
- New required env var/setting without default — not added to `.env.example`, Compose,
  Helm values, Sealed Secrets?
- Env var renamed or removed; changed meaning of an existing setting.
- Feature flags removed while still referenced.

**Auth and sessions**
- Token/cookie format, claims, cookie name or scope changed → logged-in users are
  logged out or fail.
- Permission model changed → existing users lose or gain access.

**Frontend**
- Routes/URLs changed — bookmarks, links in emails, redirects.
- Persisted client state (Zustand persist, localStorage keys) changed without
  `version`/`migrate`.
- Public exports of shared modules removed/renamed (other slices or packages break).

**Events, jobs, integrations**
- Message/webhook payload changed; job arguments changed while old jobs are queued.
- Outbound API calls to third parties changed (contract with external systems).

**Infrastructure**
- Ports, health endpoints, image names, Helm value keys renamed — deployments and
  probes break.

## Report

For each finding: who breaks, when (deploy, next login, next migration), and the
non-breaking path (deprecate first, expand/contract, default value, version bump,
coordinated frontend change). Breaking change without migration path = Blocker.
Schema: `../output-format.md`.
