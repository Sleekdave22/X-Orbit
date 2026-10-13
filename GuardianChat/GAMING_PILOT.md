# Clutch Naija — private pilot

Gaming is part of GuardianChat, sharing the existing account and server. Browser: `/gaming.html`. Android: Gaming button from the chat list, or drag from the left edge to the right. The welcome lasts up to five seconds and can be skipped. GuardianLab camera monitoring is stopped on entry; existing protected media behavior is preserved.

Set up a gaming nickname and registered game ID in Profile. Age is self-declared; this pilot is adults-only, not identity-verified. Optional winner exposure is opt-in. Names in the league are gaming nicknames, not imported real names. Handles appear on winner cards/banner only when the player opts in.

A division has eight players and 28 unique round-robin fixtures. Seven rounds each have a four-day flexible window, totaling 28 days. Start requires eight enrolled players. Points are win 3, draw 1, loss 0. Tie-breaks are points, score difference, score for, wins, nickname, account ID. Top four seed two semi-finals; winners enter the final. Knockout scores must identify a winner under agreed game rules. eFootball, EA FC Mobile, and CODM 1v1 are pilot presets, not official publisher integrations or approved tournament rules.

Results are fixture-bound. PNG/JPEG evidence is required for initial reporting (under 5 MB), with optional offline OCR assistance. OCR may suggest a score only when one score pair is found. Players must check orientation and registered game IDs. Matching player reports or explicit opponent confirmation count a result. Disputes remain uncounted until an independent league moderator reviews them. An organiser cannot approve a match in which they played. The organiser can assign another existing account as moderator. Audit records capture decisions. Screenshot access is restricted to the fixture players and league moderators. Exact duplicate images across submissions are rejected; edited duplicates, collusion, authenticity, and account ownership are not automatically proven. No silent 24-hour win award is used.

Sponsor placement is optional and marked “Supported by”. Reward descriptions default to recognition; changing a reward requires the organiser to declare it funded, and is allowed only before the division starts. There is no payment, entry fee, raffle, wallet, automatic payout, or sponsor contract. Public/commercial launch requires applicable publisher and local competition requirements to be addressed separately. This remains the existing private LAN deployment, not a public service.

Confirmed final winners who opted in appear above the chat list and link to their rank card. Browser cards export/share as PNG; Android uses its share sheet. Gaming uses GuardianChat’s grey/charcoal/oxblood styling and press sweep. Browser Gaming mode is in the top header, separate from Chats and Calls.

## Local OCR runtime

Install `server/requirements-gaming.txt` in the server's existing `.venv-push` environment. `gaming_ocr.py` uses RapidOCR/ONNX CPU with two threads, an image size cap, and one-at-a-time reading. No screenshot is sent to a cloud AI provider. If the runtime is missing or a read fails, manual reporting remains available. Models are package-bundled; do not upload private screenshots or runtime files to GitHub.

## Validation and remaining work

`python -m unittest test_gaming.py test_server.py` checks scheduler uniqueness/capacity, participant access, private evidence, pending scoring, disputes, full season/finals, feature consent, funding declarations, reward freeze, duplicate submissions, and organiser conflicts, alongside existing chat tests. Tests use disposable accounts and a temporary database, not live competition data.

A real pilot with eight participants is still needed. Screenshot templates have not been calibrated on real game screenshots. Automated reminders, promotion/relegation across divisions, per-game account linking, publisher APIs, robust fraud detection, campaign analytics, independent age verification, and a public cloud deployment are later work. The current winner feature supports gaming nickname/handle text; profile-picture and social-link expansion can follow.

## Registration, cup schedule and match rooms
Competition organisers choose league plus Finals or an eight-player knockout cup. Registration is persisted transactionally and allocates an immutable, first-registered slot. The next page displays the schedule; unfilled slots remain visibly empty. Cup starts require eight players, with slots 1–2, 3–4, 5–6 and 7–8 paired. Confirmed quarter-final winners advance to semi-finals and then the final. League round-robin scheduling uses the same stored slots. Existing divisions remain leagues; no in-progress competition format changes.

Players lists registered gaming nicknames and slots. Ongoing lists open, unresolved match windows, not proof that the players are playing at that moment. Authenticated spectators and players can join fixture-specific comment rooms. Rooms become read-only when the result closes; comments are stored on the shared server. Gameplay video streaming is not yet implemented. This local pilot currently has basic length/rate limits, not production moderation.

The explicit Dark/Light selector persists GuardianChat's shared browser appearance preference. Both the Android embedded Gaming page and browser fetch these same assets and use the same account-authenticated backend. Re-enter Gaming or refresh to load the update.

## Sponsor rank cards
Rank cards use the GuardianChat profile picture, gaming nickname and opted-in social handle. Other participants' photos remain hidden when winner-feature permission is disabled; a player can still preview their own photo. First place in a league and confirmed competition champions get a crown. Cup contenders do not receive a misleading league ranking before a winner exists. The shared PNG includes the portrait, crown and social handle.

Organisers can upload a PNG/JPEG sponsor logo under 1 MB and select a sponsor week. The current artwork remains until replaced; automatic sponsor rotation and historical campaign storage are not implemented. Without a supplied logo, the card uses a generated GuardianLab shield illustration marked as a demo sponsor, not a claimed commercial sponsorship.
