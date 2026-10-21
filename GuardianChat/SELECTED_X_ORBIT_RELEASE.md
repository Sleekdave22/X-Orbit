# Selected X_ORBIT interface and sponsored league foundation

21 October 2026. Repository: `Sleekdave22/X-Orbit`.
Branch: `fix/separate-android-installer`; original branch head `7e9e33f`.
Default branch inspected: `3b1209ef0ffc554981f3e8035a444a39d6014a37`.
No merge into main.

Latest incremental update: see `NAVIGATION_WALLPAPER_UPDATE.md` for version 7,
global account search, bottom native tabs, Settings copyright and the supplied
wallpaper. That update supersedes the earlier footer placement described below.

## Source and compatibility

The owner selected this repository's existing oxblood/gold interface. Its PNGs,
launcher icons, palette and GuardianLab engine are preserved. Working backend
services and supporting UI from `Sleekdave22/GuardianLab` at
`b0c5c2731e6ca3ee254ae69cd2d3b5ca36f89d67` are reused rather than deploying the
older fork's incompatible business logic. `server/authoritative-baseline.json`
records the imported baseline. Current gaming/studio/result helpers are adapted
to the selected CSS and new league navigation.

The Android production identity stays `com.guardianlab.chat`, retaining existing
private storage and notification setup. Version 5 replaced the old original UI
with the approved Compare interface. The owner separately approved removing the
version 4 comparison duplicate; removal succeeded. Only the production package
remains installed. Protected storage code and encryption keys were not changed
or transferred. An optional `-PorbitComparison=true` build retains the separate
comparison identity for development; it is not the production installation.

Firebase configuration is local-only and ignored by Git. A fresh checkout needs
its own matching Firebase client configuration to enable background push. No
private config, account sessions, database, TLS keys or installer binary belongs
in this commit.

## Implemented in this stage

- Native icon entry for OrbitPlay; compact gaming navigation and spacing.
- A single appearance preference controlled from chat settings, shared with gaming
  and the test wallet. The selected palette is not overwritten by old published
  defaults from the other client.
- EXIF-aware profile-photo import and an owner-controlled rotate action for an
  older image whose orientation metadata was already discarded.
- Reused camera/screen broadcasts, live directory, comments, reactions, social,
  game identity, scheduling, invitation and test-wallet services.
- Separate Sign in / Sign up choices in the browser. Refresh skips the intro;
  first-visit intro images have explicit size bounds.
- Browser Chats/Calls tabs live below the list and copyright. Both lists share
  one stable container. Presentation polling no longer moves the tabs or swaps
  list nodes around on every refresh. Existing account authentication is unchanged.

## Sponsored league contracts

`GET /leagues/list`, `/status?league=…`, `/audit?league=…`, `/appeals`.
`POST /leagues/create`, `/edit`, `/transition`, `/register`, `/queue`,
`/heartbeat`, `/queue_leave`, `/visit`, `/appeal`, `/appeal_decide`, `/resolve_void`.
Participant accept/check-in/complete/report/evidence actions reuse the existing
authenticated match engine. Existing game and chat API identifiers remain intact.

New tables use `sl_` for league lifecycle, registrations, queue, cooldowns,
completed pairs, results, standings, visit counts and appeals. Shared tables use
`gb_match_origins`, `gb_legacy_fixture_origins`, `gb_player_reservations`,
`gb_match_times`, `gb_match_cooldowns` and a migration marker.

Origin/participant snapshots are immutable. Existing open matches map to global
ranked play; legacy league fixtures are explicitly classified separately. Existing
ratings and awards are retained. New sponsored and legacy competition results
do not change global skill rating. Sponsored points are awarded exactly once:
win 3, draw 1, loss 0. No daily match cap; a verified opponent pair counts once
per league. Global and league matches share player reservations.

One ACTIVE league and one REGISTRATION_OPEN league are enforced with partial
unique indexes. Published policies are frozen; lifecycle changes use version
checks, deadlines and audit events. Matchmaking uses the actively searching,
compatible league pool without skill proximity. Queue heartbeats expire after
90 seconds. Declines/timeouts release reservations and continue eligible searches.
Disputes hold points. Unanswered review cases become void after the published
48-hour grace period, rather than treating silence as a win.

Players may request independent review of voided matches while their league is
ACTIVE or FINALISING. Administrators cannot review their own matches. Reopening
requires both players to be free, reserves both, and still requires the existing
evidence/review process before points can be awarded. Pending appeals prevent
league completion. Already completed results have no arbitrary edit endpoint.
Equal points/wins/draws share a position; no database-ID prize winner is invented.

## Verification actually performed

- Initial backend regression: 68 tests passed (core, gaming, identity/rankings,
  test wallet, sponsored leagues). Some groups were rerun after later changes;
  do not sum overlapping runs as unique coverage.
- Sponsored league HTTP/transaction tests: 8 passed, including concurrent queues,
  singleton constraints, rating separation, duplicate settlement, deadlines,
  declines, disputed-result holds and independent appeal review.
- Identity/ranking, match-stream and image compatibility run: 33 tests passed.
- Final core/identity/ranking/sponsored regression after compatibility guards:
  34 tests passed.
- Actual synthetic WebRTC transport run: 3 tests passed, including one publisher
  with six decoding viewers, authorization and cleanup. This is not proof of
  unlimited physical capacity.
- Browser script checks passed for profile/presence, live directory reconciliation,
  relay UI, screen-broadcast bridge and test-wallet safeguards.
- Android unit tests and assembly passed. Version 5 installation and saved @s21
  authentication against the shared APIs were verified. Phone UI feedback found
  the first scroll fix insufficient. Version 6 is built with pre-draw anchoring
  and numeric-only diagnostics. Version 6 installation and the saved @s21 API
  session are verified. The owner confirmed that an existing chat opens at the
  latest message. Device diagnostics recorded content height 26835, viewport 1765,
  scroll offset 25070 and bottom offset 25070: the first revealed frame was at
  the actual content bottom.
- In a separate synthetic browser fixture, league registration saved and changed
  the count from 0 to 1. Sign-in/sign-up forms switched independently. Refresh
  displayed the choices directly. Chats → Calls → Chats retained exactly the same
  tab-bar rectangle (top 703, bottom 772, height 69 in that viewport).

## Local deployment

The chosen browser interface runs on the existing shared server and database.
Migration was dry-run against a database backup: 5 users, 163 messages, one
historical open-match origin and two existing participant reservations were
retained. SQLite integrity check passed. Runtime/source/database backups are
outside Git under `local-backups/selected-x-orbit-*`.

Mac browser: `https://localhost:8766/`; gaming: `/gaming.html`.
The previous `192.168.1.171` address is no longer the Mac's current network address.
Browser storage belongs to an origin, so the old address's saved login does not
automatically appear at localhost. Mainfirst (`@sleekdavemain`) remains on the
server with its existing password. No account was recreated or password reset.

The S21 currently reaches that same server through trusted localhost with ADB
reverse. Debugging disconnects can remove that mapping. This is a test connection,
not a public hosting solution. Remaining items in
`APPROVED_IMPLEMENTATION_QUEUE.md` must not be described as complete.
