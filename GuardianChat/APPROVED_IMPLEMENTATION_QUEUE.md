# Approved X_ORBIT implementation queue

Owner selected the X-Orbit Compare appearance on 20 October 2026 and authorized
implementation, local browser/phone deployment and GitHub progress. The selected
interface becomes X_ORBIT. On 21 October the owner approved retaining the updated
original Android identity (`com.guardianlab.chat`) and removing the comparison
duplicate, so existing notification registration and app-bound keys survive.
The selected Compare styling is retained. Preserve
the shared account/database, approved icons/colours and GuardianLab protection.

## Work sequence

1. Chat opens at the latest message after layout; respect scrolling up.
2. App-icon gaming entry, compact navigation/spacing, shared chat theme setting,
   EXIF-aware photo upload and explicit correction of already-rotated avatars.
3. Browser serves the chosen interface with the existing account service.
4. Reuse current authoritative backend modules in this repository. Do not deploy
   the older fork backend or introduce a second data store/business engine.
5. Immutable match origins and transactional player reservations; legacy match
   mapping; independent reports/disputes/idempotent settlement.
6. Permanent global rating isolation; no sponsored result changes global Elo.
7. Single sponsored-league lifecycle/registration, open pool matchmaking,
   one verified encounter per opponent per league, unlimited legitimate matches,
   3/1/0 standings and explicit unresolved prize-tie policy.
8. Consolidated global/league navigation, notifications, streams and account
   integrations. Preserve wallet/history; real money remains disabled.
9. Command Center security/config/audit foundation, then operational controls,
   content/social/stream administration, automation and reporting in stages.

## Current safeguards

- User approved previous access denials; scoped filesystem/network access granted.
- Existing @s21 identity is confirmed in both clients. Current phone test uses
  the trusted localhost ADB reverse connection; debug disconnection removes it.
- The shared backend and selected interface are now integrated. Production uses
  the server's approved interface; the old read-only comparison bridge is not loaded.
- Version 5 passed installation/account checks but failed the owner's latest-chat
  scroll check. Version 6 moves anchoring to pre-draw; the owner confirmed that
  chats now open at the latest message. Device diagnostics also matched the bottom.
- Existing app-bound protected media cannot be made transferable by copying
  keys. Retiring the old app must not weaken that rule or claim recovery.
- New league prize ties must not be decided by registration time or database ID.
- Existing legacy league/rating records are retained; no silent historical reset.

Each stage must record actual tests, migration effects, commit and deployment
status. This file is a queue, not a completion claim.

## Remaining work after this release stage

- Build the Command Center's scoped roles, privileged-session/MFA controls and
  audited operational modules from the approved handoff in separate tested stages.
- Add sponsored standings pagination and large-pool load testing before claiming
  large-scale readiness. Current correctness checks use small isolated groups.
- Add controlled reversal/recalculation for already-finalized results. Current
  appeal review handles voided matches before league completion; it cannot silently
  rewrite completed leagues or global history.
- Validate screen broadcasting, incoming calls and notifications end-to-end on the
  final phone installation with another signed-in participant.
- Replace the temporary ADB reverse connection with stable trusted LAN addressing
  for ordinary phone use without debugging; remote/public hosting is separate work.
