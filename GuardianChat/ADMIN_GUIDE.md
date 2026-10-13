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
