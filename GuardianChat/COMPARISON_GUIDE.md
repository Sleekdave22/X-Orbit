# X ORBIT — two-app interface comparison

20 October 2026. Preserve the two designs while using the existing server and
accounts. The new Global Ranking / Sponsored League handoff is deferred until
the owner has compared both apps and chosen which interface to continue with.

## The two repositories

| Installed name | Source repository | Inspected baseline | Local source |
|---|---|---|---|
| **X ORBIT Original** | [Sleekdave22/GuardianLab](https://github.com/Sleekdave22/GuardianLab) | `feature/orbit-match-live-relay`, `59b70059a7f3c7c846570cfc733eb949afb57046` | `/Users/mac/Documents/Codex/2026-10-09/ca/OrbitBrandingPhase1/GuardianChat` |
| **X ORBIT Compare** | [Sleekdave22/X-Orbit](https://github.com/Sleekdave22/X-Orbit) | remote `main`, `3b1209ef0ffc554981f3e8035a444a39d6014a37`; comparison work on `fix/separate-android-installer` | `/Users/mac/Documents/Codex/2026-10-09/ca/XOrbitStandalone/GuardianChat` |

These repositories share earlier code, but their recent work diverges. A later
date in X-Orbit does not mean it contains every improvement from GuardianLab's
feature branch. Compare source and behavior rather than treating either repo's
name or `main` branch as an automatic replacement for the installed app.

The current backend remains authoritative for account IDs, profiles, contacts,
messages, gaming identities, matches, rankings, wallet records and permissions.
This comparison does not start an X-Orbit backend or run its database migrations
against live data.

## Trace of the differences

The following changes are supported by local commit metadata and present source.
Commit authorship identifies the recorded contributor; it does not prove that a
change was built, installed or tested on the S21.

### GuardianLab: current original baseline

| Commit | Date | Change |
|---|---|---|
| `f1b5410` | 19 October | Live matches update in place, retaining cards, focus and drafts rather than rebuilding the page at each poll. |
| `429a3bd` | 19 October | Revocable account signup links across browser and Android, separate from game invitations and contact codes. |
| `ca67e06` | 19 October | Ranking-engine audit and migration plan; documentation, not implementation of a new rating formula. |
| `59b7005` | 19 October | Restored “Why play for play when you can play for pay?” in the gaming header and switching experience. |

Original additionally contains separate identity, scheduling, ranking, wallet and
streaming modules, including `server/game_identities.py`, `match_scheduling.py`,
`rankings.py`, `wallet.py` and `stream_relay.py`. Its native build declares the
WebRTC SDK used for gameplay broadcasting. Retain the working shared backend
rather than replacing it with a fork backend solely to view a different design.

### X-Orbit: design and competitive changes

| Commit | Date | Change and comparison implication |
|---|---|---|
| `2dd47db` | 19 October | Oxblood/gold theme, icon-led Orbit Play intro and scaled promotion/table zones. |
| `51c5cd9` | 19 October | New 1,000-start Elo formula, K40/K20, 20 provisional matches, immutable rating history, skill tiers and a Ratings tab. These are fork backend changes; opening its interface on the shared backend does not activate them. |
| `436c914` | 19 October | Renamed the chat entry button to Orbit Play. |
| `30de3c1` | 19 October | Eligibility snapshots/cutoffs, per-game tiers, widening matchmaking, abuse flags, reliability, result reversal, withdrawal, cup seeding, head-to-head data, grouped tabs and Studio controls. Review integration before adoption. |
| `9951406` | 19 October | Added `RUN_IN_ANDROID_STUDIO.md`, recording that the redesigned Android code had not yet been compiled by its author. |
| `b27f48d` | 20 October | Propagated oxblood through browser chat and published theme defaults, including legacy theme/label migration. |
| `616d80d` | 20 October | Applied oxblood/gold across native chat and protection presentation; refined ivory light mode and settings, call and profile contrast. Preserve this fork's appearance for comparison. |
| `460568f` | 20 October | Registration-first gaming entry and backend profile prerequisites. |
| `8fd0213` | 20 October | Carried a registration game ID to games and collapsed the identity form after saving. |
| `3b1209e` | 20 October | Superseded the preceding single-ID approach: collect a separate ID for each game and require the relevant game's identity when joining a league. |

`51c5cd9` and `30de3c1` are recorded as authored by Claude, with original session
references in Git metadata. This sequence explains the fork's different design
and behavior despite originating from the same application.

The inspected fork's `server/gaming.js` retains an older private streaming
test-room interface, with a five-viewer description. Original has the newer
discoverable match streams and relay. An older screen or its wording does not
mean the shared server lost the newer streaming engine.

## Why a separate installer needs changes

Both baselines originally used Android application ID `com.guardianlab.chat`.
Installing both unchanged would update/replace the same package; it would not
create two launcher apps. The internal namespace can remain unchanged while the
comparison package uses `com.guardianlab.chat.compare`.

The repository contains `chat`, `guardianlab` and `guardianlab-ui` modules,
Gradle configuration and engine source. An interrupted partial clone and
incomplete checkout/build preparation are not evidence of an absent engine.
Open/build the nested `GuardianChat` project for messaging; the outer repository
root configures the separate detector `app` module.

Comparison packaging is limited to a distinct application ID/launcher label,
bundling the fork's web interface, and a narrow response-compatibility bridge.
Original keeps its package, account storage and installation; its launcher label
distinguishes it from Compare. Do not change PNGs, icons, logos, approved palette
values or GuardianLab detection/security logic to make a second installer.

## Shared backend, preserved interface

Loading the current server's `/gaming.html` in both apps would show the same
server-hosted gaming interface. Compare therefore needs its bundled X-Orbit
interface while authenticated requests continue to use the current server.
The compatibility bridge may adapt response shapes for display; it must not
invent verified results, grant permissions, apply the fork's rating formula,
silently publish a theme or mutate shared data on page load.

Keep the fork's grouped navigation, registration arrangement, oxblood/gold
colors, ivory light appearance and existing assets. Some fork-only controls rely
on backend contracts absent from the current server. Unsupported operations must
explain the limitation or remain unavailable; they must not pretend to save.
Displayed counters and result/rating values must come from the current backend.

Both apps use the same server URL and can sign into the same existing account.
They have separate Android storage and login sessions. Signing into Compare does
not copy Original's private storage or overwrite its saved login. Messages,
native profile changes and other authorized native-chat writes in either app
affect the same account on the shared server. Competitive, identity, result,
stream-control and administrative writes in Compare's gaming interface are
view-only for this comparison and explain that editing is available in Original.
This prevents the fork's different contracts from changing shared rules or bypassing
reviewed identity changes. Avoid deleting chats, resetting
invitations, publishing Studio settings or submitting test scores merely to
compare appearance. The same account in both apps is still one match participant;
a second existing account is needed for a two-person test.

### Explicit comparison limits

- Fork backend features await deliberate adoption; a separate client installation
  does not activate them.
- Background Firebase delivery for Compare needs an authorized Firebase Android
  client matching the new package. Original's registration must not be reused
  under a mismatched package or described as verified for Compare.
- Protected media keys are app-private and device/app bound. They are not copied
  from Original to Compare. Previously device-bound media may remain accessible
  only in the original receiving app. Do not weaken protection for comparison.
- The existing Mac/Wi-Fi server remains the service address. A second installer
  does not make it publicly hosted or reachable outside that network.
- A build or installation alone does not prove every game, protected viewer,
  notification or broadcast works on the physical phone.

## Manual comparison

1. Open **X ORBIT Original**, then **X ORBIT Compare** from the launcher. Confirm
   Compare has not replaced Original.
2. Sign into Compare with your existing account and current server address.
   Check that account ID, profile name and contacts agree with Original.
3. Compare the native intro, chat list, profile, settings and light/dark modes.
4. Open Orbit Play in both. Compare the header, grouped navigation, registration
   form, leagues, profile card and button spacing.
5. Check shared data agrees. A fork-only rating display must not claim its new
   rating policy is running when the current backend still uses its own policy.
6. Use a second account for invitations/streams. Check background delivery
   separately from an invitation appearing while the app is open.
7. Choose the interface to continue with. Only then begin the new handoff's audit,
   architecture/migration plan and staged implementation in that repository.

## New handoff is deferred

Attachment `85203b01-9be7-40ec-a229-383bcbc5e3ec` targets permanent Global Ranking
and one active Sponsored League: isolated match origins, unique league opponents,
accumulated league points and transactional verification. It is a specification,
not a claim that the fork already meets it. No Sponsored League refactor,
rating-policy migration, real-money feature or new prize distribution is part of
this comparison. Preserve existing users and histories while the owner chooses.

## Build, installation and verification record

Builds and isolated integration verification completed on 20 October:

- Original `:chat:assembleDebug`: passed (23 seconds). Original's source change
  is its launcher label; package `com.guardianlab.chat` and saved data stay intact.
- Compare `:chat:testDebugUnitTest :chat:assembleDebug`: passed. The first packaging
  attempt found AGP's unsupported Provider-valued legacy source directory; using
  an explicit generated directory with a preBuild task dependency fixed it.
- Four Android routing tests passed, covering exact static allowlists, API/media
  passthrough, foreign origins, encoded traversal and HTTPS port handling.
- Eleven JavaScript compatibility checks passed, including current-server rating
  values/history, account-scoped read caching, incompatible-write blocking,
  successful/failed server responses, shared chat passthrough and theme retention.
- An isolated synthetic-data browser check rendered grouped navigation, leagues,
  Ratings, Admin Studio and ivory light mode. A real verified fixture in that test
  database displayed the current policy's `1500 → 1512 (+12)`, ten placements and
  K24, rather than falsely applying the fork's K40/1000 policy.
- Eight bundled scripts/styles/images/fonts match their fork source bytes. The
  fork's original HTML, styles, icons and fonts remain unchanged in Git. Only the
  generated APK HTML injects the compatibility bridge and render hook.
- APK manifest inspection confirmed the distinct Compare package and launcher
  label, correct activity class and package-specific clipboard provider.
- No current-server backend files, database migrations, GuardianLab detection
  code or source palette assets were changed.

| APK | SHA256 |
|---|---|
| X ORBIT Original | `fc5fb55ef6e1498ebafd762eef3da13590df537e3ae3eb794243f5afc84172d4` |
| X ORBIT Compare | `786ff15b4ce4fb8593e5383c311431799486e9dcb95f8d02680ccdab5384c298` |

Phone installation/hash comparison and the user's physical interface comparison
are pending. Record actual installation results before claiming completion.
