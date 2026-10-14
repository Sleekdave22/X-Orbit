# Gamebox handover audit and implementation tracker

Specification: Gamebox_Complete_Updated_Handover_2026-10-13.docx.

The user authorised implementation of the document. The later direct instruction keeps administration restricted to Mainfirst (@sleekdavemain), rather than exposing administration to all organisers. The accepted top-three-up/bottom-three-down rule remains in place; medals are separate from divisions.

## Audit of the starting build

Already present: shared GuardianChat accounts/contacts, Android/browser gaming entry, optional gaming identity, eight-player round robin and cups, fixed participant snapshots, proof review, standings, promotion events, genuine counters, rank cards, opt-in winner features, private two-account streaming tests, single-account admin access. GuardianLab is used only in protected viewers.

Missing or limited: open matchmaking, independent typed score workflow without routine screenshots, official IDs per game, scheduling/check-in, no-show recovery, persistent configurable policies, versioned Theme/Page Studio, season-wide grouping, qualifier allocation, appeal workflows, production queues and Android game-screen broadcasting.

## Implemented in this batch

- Versioned Studio drafts, supported theme preview, publish and rollback. Colours, built-in fonts, sizing, announcement, optional statistics visibility and safe component order. Existing stored settings are not overwritten on restart.
- Bounded policy settings for proposal acceptance, check-in, submission/evidence windows, retention, reminders, rescheduling, group target, round duration, opponent-repeat limits and rating gap.
- Separate official gaming IDs per game, region, time zone, availability and reminder preference.
- Open matchmaking by game, declared region, rating gap and repeated-opponent history. Both accounts accept, then both check in. A ready/accepting player's expired proposal returns them to a priority queue; a replacement still requires dual acceptance.
- Fixed score order and independent typed reports. Matching reports verify immediately. Conflicts or unanswered deadlines go to evidence/review, never an automatic win.
- Persistent per-game Elo skill rating (K=24), separate activity points, and idempotent rated-result processing. New played competition results also update rating; old competitions are not retroactively rated.
- Match-linked communication cards/rooms with a single authoritative record.
- Private, original disputed evidence; server-side screenshot-reading aid; independent admin decisions with original reports and corrections in the audit. Ordinary new verified evidence has configurable expiry. This is application-level deletion, not a forensic secure-erasure guarantee.
- Opt-in season registration windows, eligible gamer notices, balanced groups generated at close, snapshot IDs, skill ordering within qualified divisions, controlled registration extensions and conflict/insufficient-entry review.
- Weekly-open qualification derived from verified wins, opponents and participation; major cup slots configurable between league performance and weekly opens. No fabricated qualifier slots.
- League groups configurable from 6–16 players, including 10-player/nine-round schedules. Odd groups have byes. Cups remain eight-player knockout. Old competitions retain original capacity, timings and verification mode.
- Both league opponents propose/confirm a time within overlapping registered availability. One mutual reschedule by default, with a cutoff. Both check in before reporting in new competitions.
- Documented league no-show review: only the player who actually checked in may receive a walkover; double no-shows yield no points. Neither changes skill rating. No silent opponent replacement in league fixtures.
- Server-driven expiry and reminder events independent of mobile screens remaining open. Generic Android notice push, bounded retries, session-scoped recipients and a separate alert preference are implemented; real-device delivery still needs verification.
- Administrator-only competition size/schedule simulator. It calculates estimated balanced-group counts, fixtures, rounds and duration; it is not a load test or a promise that availability will fit.
- Open played outcomes are included in genuine player performance records and aggregate counters.

## Remaining specification work (not claimed complete)

1. More sophisticated availability/latency optimisation during automatic grouping. Groups currently use qualified division and rating order; availability overlap is enforced when scheduling fixtures.
2. More cup formats and configurable tournament templates beyond the implemented eight-player knockout and qualification-only major cup.
3. Full appeal cases, evidence-response deadlines and review decisions that fairly handle an appeal against an already verified result. Verified scores remain immutable in the current UI.
4. Production anomaly/collusion analysis, reliability flags and richer eligibility administration. Current safeguards are game-ID uniqueness, session checks, repeat-opponent caps, immutable evidence and audit trails.
5. End-to-end device testing of new match-notice push delivery and registration announcements. Generic Android Gamebox push handling is implemented; real delivery still needs verification on the S21.
6. Streaming from the Android game screen, more spectators, game audio, internet relay/SFU and stream moderation. The prior private two-account desktop-screen-sharing test remains available, with real-device end-to-end testing pending.
7. Rich free-form page building, custom icon/font uploads and competition-template libraries. Current layout editing only reorders supported components and hides optional stats; it cannot change privacy/security controls.
8. Scale/abuse load testing and public deployment. The service remains a Mac-hosted same-Wi-Fi pilot; simulation alone does not establish capacity.

## Migration and safety constraints

Additive SQLite tables/columns; legacy fixtures and chat/media data are preserved. New competitions use typed verification and check-in. Existing competitions retain proof-based legacy rules. Rankings/counts have no arbitrary edit controls. Admin access remains server-side and tied to the configured account. No production GuardianLab model, capture protections, account credentials or encryption policy are changed by Studio.

Tests cover authentication, invalid Studio fields, stale drafts, publish/rollback, restart persistence, dual acceptance/check-in, matching reports, duplicate verification, unanswered reports, private/immutable evidence, independent review, retention events, larger round robins, no-show points without rating and simulator calculations.

## X ORBIT live camera and invitations — 14 October 2026
- Private camera-and-microphone rooms replace screen sharing in the LAN pilot. Invited members can comment and like once per account; targeted signaling prevents viewers receiving another viewer’s negotiation. Room broadcaster can add up to five viewers. Camera stops on room exit or backgrounding. No media recording is saved; comments and likes are server data.
- Android WebView capture is allowed only for the configured HTTPS origin after Android camera/microphone permission. Actual multi-device playback and sound still require device testing.
- Find a match includes direct game invitations with accept/decline, expiry, official identity checks, active-match limits and hourly invite limits. Notices use existing browser alerts and Android Gamebox push delivery. Physical receipt and sound remain to be checked.
- Removed duplicate native Gamebox toolbar; the web page keeps its own header and back navigation.
- Validation: 16 gaming tests (including room membership/comment/like/privacy) and 12 match-engine tests (including direct invite acceptance/decline) passed.
