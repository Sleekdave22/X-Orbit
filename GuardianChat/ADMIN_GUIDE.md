# Gamebox administration

Open GuardianChat Settings → Gamebox administration. Browser shortcut: `/gaming.html?admin=1` on your existing server. Sign in with the same account used to create the competition. Organisers see their own competitions; assigned moderators see their assignments. Creating an account does not give it administrator access to other competitions or private chats.

## Routine controls

1. Choose **Manage** beside the competition.
2. **Results, evidence and organiser tools** opens the Matches page. Expand Organiser tools to assign moderators, change sponsor details, upload the weekly sponsor logo and announce a secured reward. Rewards can only change before the competition starts.
3. **Registered players** shows server-assigned slots. **Match schedule** shows fixed fixtures and bracket advancement.
4. For a pending or disputed result, select **Review evidence**. Inspect the original screenshots, submitted scores and original screenshot-reader text. Enter the corrected final score and an explanation. A moderator cannot approve a match they participated in.
5. In **Match-room moderation**, hide an inappropriate comment with a reason. The original is retained in the moderation view, and the action is logged.
6. Review **Audit history** for submissions, approvals, score corrections, moderator assignments, sponsor changes and hidden comments.

The organiser can remove a moderator using their GuardianChat nickname or unique ID. Removing a moderator revokes future dashboard access; it does not rewrite earlier decisions.

## Automatic score reading

Screenshot upload attempts local OCR and fills the score boxes when exactly one score pair is found. Unclear readings require manual entry. The screenshot remains the evidence: OCR is not proof that an image is authentic or that a score belongs to the scheduled match. Matching player reports or independent review determine acceptance. Moderator approval logs the original reports, approved score and reason. Confirmed matches cannot be edited or approved again through the dashboard.

## Things the dashboard intentionally cannot edit

- Original screenshots, registered game-account snapshots and assigned player slots.
- Confirmed match scores, winners, finished standings or audit entries.
- Other accounts' passwords, private chats, view-once or protected files.
- GuardianLab models, detection thresholds, encryption, permissions or certificate trust.
- Software code, database schemas, payment balances or real prize disbursements.

Competition names can change before start. Sponsor artwork can be replaced as campaigns change; the sponsor week identifies the current artwork. This is not an automatic sponsor rotation service.

## Operating without a developer

Competition administration does not require a new APK or a code change. The browser and Android dashboard use the same server data. Keep the Mac server running and reachable on the same Wi-Fi for this local version. An internet hosting service is a separate deployment task.

Changes to application features still require software development, testing and installation. When adding a future feature, its administration controls must enforce permissions on the server, validate inputs, log mutations, and explicitly identify immutable fields. Add permission and abuse tests before releasing those controls. Do not add a generic SQL editor, arbitrary account impersonation or an editable winner field.

This audit is enforced by the application. A person with unrestricted access to the Mac/database can still modify files directly; it is not cryptographically tamper-proof. Production operation should separate hosting/database permissions and keep independent audit backups.

## Single administrator and statistics
Administration is now restricted to the Mainfirst account (@sleekdavemain). The local ignored `server/data/admin_account.txt` identifies the administrator, and the server enforces it. Other accounts cannot open the dashboard or perform administrative actions, even if they created older competitions. Existing moderator assignments do not grant access under this single-administrator rule. Independent result review still refuses matches involving the administrator; those matches need matching player reports.

The dashboard counters are derived from stored records: users, gaming profiles, unique registered players, registrations, competitions, active/completed competitions, league/cup titles, unique winners, fixtures, confirmed matches, disputes, pending results, evidence uploads, promotion/relegation events, assigned moderators and comments. These are the implemented counters, not a claim to capture every possible future statistic. Gaming pages show selected game counters. Contact cards show confirmed wins/losses/draws/titles and the five latest confirmed outcomes.

All players start unranked, qualified for Open. After a league (including its Finals) finishes, the top three in its league standings move up one division, the bottom three move down one, and the middle two stay. The current levels are Open, Division 2, Division 3 and Premier. Open and Premier are the lower and upper limits. Cup results do not change league divisions. Qualification is separate for each game and cannot be edited through the dashboard. Gold/Silver/Bronze denote first/second/third place, separately from divisions.

The latest active promotion policy is top three up and bottom three down. It overrides the earlier top-two/bottom-two proposal. Only the authorised account has the Administration tab and dashboard API access.

## Two-account streaming test
Open Gamebox → Streaming test as the administrator, enter the second account's nickname or unique ID and create the room. Sign into that second account on the S21 or another browser, open Streaming test and enter the same room. On the broadcasting desktop browser, click Share game screen and choose the game window in the browser's picker. The viewer may need to press Play.

This first test uses peer-to-peer WebRTC on the same Wi-Fi, video only (no game audio), with one broadcaster and one viewer. Rooms expire after two hours and admit only their two accounts. Screen capture always requires the browser picker. Android's embedded page can receive video; broadcasting the Android game screen is not implemented yet. It requires Android MediaProjection integration. More spectators and a cloud relay are also separate work. No gameplay recording is saved, and test streams do not affect scores or ranking. End-to-end screen sharing still needs testing on your actual two devices.

## Handover update: Admin Studio and open matches

Gamebox now has **Find a match** and **Admin Studio**. Register each official game ID and future availability in Find a match. Queueing declares that you are ready for an open opponent now. Both players accept, check in and submit scores in the displayed fixed order. Neither player can replace the opponent or award a result by silence.

In Admin Studio, save a draft, preview its supported theme, publish with a reason, or roll back to an earlier published version. Settings remain on the server across deployments. Each open match keeps its original policy version. Theme edits apply to Gamebox, not GuardianLab protection or native GuardianChat security settings.

New leagues can have 6–16 players; the default Studio target is 10. Create a separate group rather than a giant table. Old leagues retain their rules. For a new league fixture, both players must register overlapping availability, agree its proposed time and check in near that time. Routine matching independent scores need no screenshot; disputes still require original evidence.

The server generates match notices and reminders even if phones are closed. Android push delivery is integrated; actual Gamebox alerts still need real-device verification. Keep the Mac/server awake. See HANDOVER_IMPLEMENTATION.md for the remaining handover work; the full specification is not claimed complete.

## Seasons and qualified major cups
Use Seasons to create a registration window. Eligible gamers are notified, but each registers themselves. They must first save an official game ID and availability in Find a match. When registration closes, the server creates balanced groups using the configured group target and skill order within the qualified division. Too few entrants, an eligibility change or a conflicting active league sends the registration to review. No player is silently substituted. The administrator can extend an unstarted registration window with a logged reason.

Admin Studio can allocate eight major-cup slots between recent completed league performance and the current Nigerian-calendar week's verified open results. Minimum weekly matches and distinct opponents are configurable. The cup is created only when there are enough distinct qualified players; those players must still opt in. Cups currently remain eight-player knockout.

## Visual app editor
Sign in as Mainfirst, open Gamebox → Admin Studio. At the top, Visual app editor lets you drag the existing chat-home blocks and Gamebox tabs or use their up/down arrows. Edit brand, slogan, search label, Gamebox label, and the four theme colours; the preview updates without affecting other users. Save visual draft keeps edits private to administration. Publish design for everyone saves and publishes that draft with your reason. Use Published versions to roll back. Users pick up layout and labels on browser reload or app reopen; Android caches published settings for offline use and checks at most every 30 seconds when opening the chat home. Personal light mode stays available. This is a component editor, not a free-position canvas: moving arbitrary controls, creating new functional pages, and changing protection or trusted records are not supported.

### Add a new button / section
Visual app editor → ＋ Add button / section. Enter a name, pick a function and add it to the draft. Options: content page, existing feature, HTTPS website, or a new game using numeric 0–99 score reporting. Added buttons inherit the shared Gamebox navigation styling and show to users only after publication. Up arrows reorder custom buttons; Remove from draft removes navigation without deleting registered game identities or results. Save visual draft persists your work; Publish design for everyone deploys it to the browser and Android Gamebox page. Arbitrary code, new publisher API integrations and different scoring mechanics require implementation.
