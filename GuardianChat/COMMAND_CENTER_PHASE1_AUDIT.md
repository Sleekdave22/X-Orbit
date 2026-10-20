# X ORBIT Command Center — Phase 1 audit and architecture

20 October 2026. Audit/proposal only. No Command Center implementation, league
rule migration, financial activation or replacement of the shared backend is
included. Major implementation requires the owner's review and approval.

## Repository and runtime boundaries

- Requested repository: `Sleekdave22/X-Orbit`. Remote `main` was verified at
  `3b1209ef0ffc554981f3e8035a444a39d6014a37`.
- Comparison branch: `fix/separate-android-installer`, audited baseline
  `5dc3a73297f138ba88ba22829212bb4b7f739b0e`.
- Source paths below are relative to this `GuardianChat/` directory.
- The installed Compare client bundles the fork's appearance but reads the
  existing GuardianLab server. Its competition/admin writes are deliberately
  blocked (`server/comparison-compat.js:122`). It is not an operational admin
  deployment.
- The current shared server contains later identity, scheduling, wallet, social
  and streaming modules absent from this fork. Reuse that service; do not deploy
  this fork's older backend over the live database to obtain its appearance.

## Existing capability inventory

"Verified" below means the named automated HTTP test passed in an isolated
temporary database. It does not imply production readiness or a complete manual
browser test. Other findings are source inspection, with their limits stated.

| Capability | Status and evidence |
|---|---|
| Studio save, publish, version conflict detection, persistence and rollback | Implemented and verified in an isolated HTTP test. `server/gamebox_core.py:65`, `:252`; `server/test_gamebox_core.py:48`. |
| Bounded appearance configuration and admin-only publication | Implemented and verified by an isolated test. `server/test_gamebox_core.py:149`; configuration validation at `server/gamebox_core.py:65`. |
| Admin comment moderation and audit | Implemented and verified by an isolated test. `server/test_gaming.py:127`; frontend handlers at `server/gaming.js:70`. |
| Studio preview, labels, reordering, supported sections and theme editor | Partially verified: backend configuration tests pass; current browser interaction not retested. `server/studio.js:16`, `:24`. |
| Matchmaking policy controls | Partially implemented. Existing deadlines, reminders, reschedule and rating-gap limits are validated; some operational values remain hardcoded. `server/gamebox_core.py:3`, `:151`; `server/studio.js:2`. |
| Competition policy snapshots | Implemented in source; no new end-to-end test in this audit. `server/gamebox_core.py:164`, `:287`, `:400`; `server/gaming.py:224`. |
| Counters and admin overview | Partially implemented. Real aggregate queries exist; retention, activity windows, infrastructure costs and historical analytics are missing. `server/gaming.py:443`; `server/gaming.js:70`. |
| Competition creation, sponsor/reward content and pre-start changes | Partially implemented. Backend and UI handlers exist, but the proposed single-league model is absent. `server/gaming.py:212`, `:246`; `server/gaming.js:33`, `:70`. |
| Evidence, disputes and decisions with reasons | Partially implemented. Existing privacy/moderation logic can be reused, but appeals and complete correction/recalculation workflows need review. `server/gamebox_core.py:141`, `:389`; `server/gaming.py:383`. |
| Privileged audit history | Partially implemented. Actor, action, reason and changes are recorded, but append-only protection and a full security-event model are missing. `server/gamebox_core.py:36`, `:62`, `:269`; `server/gaming.py:81`. |
| Founder authorization | Partially implemented. Server-side founder checks exist. Mandatory MFA, privileged session expiry, step-up verification and staff capabilities are missing. `server/server.py:55`, `:150`, `:168`; `server/gaming.py:29`, `:79`. |
| Moderator assignment | UI/backend mismatch: assignment is stored, but `mod()` delegates to the founder admin check. Assigned moderators do not receive the advertised independent role. `server/gaming.py:19`, `:80`, `:259`. |
| Sanctions, tier settings, integrity decisions and rating reversal | Backend-only operations, not complete founder workflows. No corresponding controls found in the audited Studio/gaming frontend. `server/gamebox_core.py:360`. |
| Scheduled announcements, audience targeting, cancellation | Missing as a complete workflow. Existing notices and retry bookkeeping are reusable. `server/gamebox_core.py:37`, `:512`, `:537`; `server/gaming.js:109`. |
| Basic/Advanced modes, user support cases, platform flags, regional staff, cost dashboard | Missing as complete Command Center capabilities. |
| Financial administration | Missing from this fork. The shared server's existing test-wallet ledger must be audited and reused rather than recreated. Real money remains disabled. |

## Conflicts and defects to resolve before adoption

1. **Earlier league handoff remains deferred.** The fork permits three unfinished
   competitions per owner (`server/gaming.py:217`), multiple registration windows
   (`server/gamebox_core.py:294`) and multiple league groups (`:485`). There is no
   database constraint enforcing one active platform league.
2. **League/global rating separation is absent.** Confirmed competition fixtures
   feed `gb_ratings` (`server/gamebox_core.py:529`). The deferred handoff requires
   explicit immutable match origins and league results excluded from global Elo.
3. **Automation override in the fork.** `ChatServer.service_actions()` at
   `server/server.py:71` invokes Gamebox work, but the second definition at `:127`
   replaces it and only expires media. Direct `tick()` unit tests do not verify
   real server scheduling. Do not replace the current working backend with it.
4. **Rating correction is incomplete.** Reversal subtracts historical deltas from
   current ratings without replaying later dependent results
   (`server/gamebox_core.py:380`). Transaction-row-based W/D/L totals also need
   reversal handling (`:129`). This must not become a casual admin edit field.
5. **Privileged access is insufficient for a public Command Center.** Existing
   bearer sessions have no privileged expiry/MFA model. Hiding a tab is not
   authorization; every operation requires a server-side capability check.
6. **Eligibility direction needs a policy decision.** The earlier handoff called
   for open sponsored-league entry; the new document lists configurable minimum
   ranking eligibility. Keep open entry as the existing proposed default unless
   the owner explicitly approves a restriction. Registration and active-league
   state boundaries also need definition before singleton constraints are added.

## Recommended architecture and proposed contracts

Extend one authoritative backend/database. Add a private `/admin/` web shell
with Basic and Advanced navigation; reuse approved appearance components and
existing domain operations. Interface mode never grants permissions.

Proposed additive storage, subject to migration review:

- Role/capability grants, revocation and privileged session records; MFA enrollment
  and recovery records with protected secret material and recovery procedures.
- A typed configuration registry and immutable revisions: key, type, bounds,
  permission, activation policy, affected services and rollback behavior.
- Append-only privileged audit events and controlled correction requests.
- Durable jobs/outbox records with idempotency keys, leases, retries and errors.
- A transactional active-league slot/constraint, plus immutable match origins,
  only after the separate league architecture is approved.
- Versioned operational metric definitions; event/aggregate storage only where
  a real source exists. Missing measurements display unavailable, not zero.

Proposed API families (not implemented):

| Family | Contract |
|---|---|
| `/admin/session`, `/admin/mfa/*` | Strong authentication, MFA, expiry/revocation and step-up grants. Never expose MFA secrets in ordinary profile APIs. |
| `/admin/overview`, `/admin/health` | Permission-scoped real metrics with source, measurement time, delay and estimation labels. |
| `/admin/config/*` | Read schema, validate/preview, save draft with base revision, publish with reason/effective time, and audited rollback. Reject conflicting revisions. |
| `/admin/leagues/*`, `/admin/matchmaking/*` | Validated commands through existing competition services, expected version and idempotency key. Freeze started-competition policies. |
| `/admin/disputes/*`, `/admin/accounts/*` | Least-privilege review/decision actions with reasons, evidence access checks, appeals and audit events. No unrestricted private-message viewer. |
| `/admin/notices/*`, `/admin/jobs/*` | Preview, authorized audience, schedule/cancel, delivery deduplication and visible failure states. |
| `/admin/finance/*` | Read-only test-ledger/reconciliation visibility initially. No arbitrary balance mutation or real-money activation. |

Use authenticated, expiring administrative sessions with CSRF protection where
cookies are used, server-side validation, rate limits and immediate grant
revocation. Do not expose shell access, raw database editing or credentials.
Ranking rules activate at a new season; rollback must not silently rewrite
finalized results. Supported corrections use audited reversals and recalculation.

## Implementation order, acceptance and recovery

1. Confirm chosen interface and authoritative backend, then map fork/current
   capabilities before porting any admin code.
2. Privileged security, capabilities and audit/config foundations. Acceptance:
   missing MFA, expired sessions, revoked roles and unauthorized APIs are rejected.
3. Approve league/global-ranking design, then additive migrations and concurrency
   protection. Acceptance: simultaneous activation cannot produce two leagues;
   league results cannot change global ratings.
4. Operational overview, disputes, user support and supported configuration.
   Acceptance: each control changes the intended backend value; failures remain
   visible; no decorative success messages.
5. Appearance/social/stream/announcement administration. Acceptance: preview is
   isolated, stale drafts conflict, publication and supported rollback work.
6. Advanced reporting, regional/staff operations, automation and test-finance
   visibility only after data/permission contracts are verified.
7. Browser/mobile regression, concurrent changes, rollback and failure tests;
   staged deployment with explicit approval and recovery evidence.

Before migrations, take a consistent database backup and verify restoration in
an isolated environment. Keep old clients compatible through additive changes.
Release behind server-enforced capabilities/feature flags; stage a pilot founder
account before other roles. Roll back code/config independently; never restore
an older financial or match database over newer authoritative records casually.

Founder workflow after approved implementation: authenticate with MFA, review
Basic overview, choose the relevant operation, preview/validate, save a draft,
publish with a reason, and check audit/delivery status. Advanced access exposes
only the capabilities granted to the signed-in role. This is the proposed
operating model, not a claim that the full console exists today.

## Validation performed in this audit

Four existing tests passed against temporary fork databases on 20 October:

- `CoreTest.test_config_permissions_revision_and_persistence`
- `CoreTest.test_visual_presentation_is_bounded_and_admin_only`
- `CoreTest.test_simulator_and_configuration_guardrails`
- `GamingTest.test_admin_scoping_and_comment_audit`

Result: four tests, 4.270 seconds, OK. These tests do not cover mandatory MFA,
the proposed one-league constraint, full frontend controls or production safety.
No league rules, scores, balances, user permissions or live admin configuration
were changed during this audit.

**Phase 1 stops here. Approval is required before major Command Center work.**
