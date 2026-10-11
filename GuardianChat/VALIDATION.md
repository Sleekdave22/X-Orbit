# First test build — 11 October 2026

## Passed

- ARM64 Android debug build; final APK installed successfully on Samsung S21 (SM-G991U1).
- 37 copied detector/controller library unit tests and 5 shared UI unit tests, zero failures.
- 3 backend integration tests: registration/token rules, invalid invite/recipient, real message and attachment transfer, sender retry deduplication, recipient isolation, attachment access, invalid/oversized payloads. Passed after adding browser companion route.
- Real Wi-Fi account registration from S21 at Mac server 192.168.1.171:8765.
- Browser-to-S21 and S21-to-browser messages verified in both rendered UIs; user also exchanged messages during testing.
- Text attachment sent through browser file chooser, received and opened in Android in-app viewer.
- Manual hide removed that attachment text from Android accessibility hierarchy and exposed only mask label.
- Audio WAV attachment received and Android MediaPlayer prepared with playback controls; playback not used as an efficacy test.
- Image attachment delivered and listed; image preview smoke test not conclusively completed.
- Camera permission granted for test session; live monitoring produced phone-risk masking/guidance and subsequently active-monitoring state. These are integration observations, not ground-truth detection accuracy measurements.

## Not established

- Native iOS GuardianLab integration or actual iPhone Safari compatibility: companion built and browser-tested, iPhone test is next.
- Recorded voice-note capture, arbitrary video codecs, full PDF/file preview compatibility, file exports, long-run reliability or two Android devices.
- Detection accuracy, unseen glasses performance, false alarms/hour, battery drain, thermal endurance or latency distribution.
- E2EE, internet deployment, background delivery notifications, account recovery or production security.

The original GuardianLab project was read and its libraries copied into this separate project. No candidate glasses model was deployed. No GitHub push occurred for this new project. Local invitation code and server account data are excluded by .gitignore. The Mac server is running for the test; keep it awake or restart with start-server.command.

## View-once update — 11 October 2026

- Version 0.2-view-once debug APK built successfully and installed on S21.
- Five backend integration tests passed, including atomic recipient-only opening, redacted chat listings, refusal of repeat opens, file leases and revocation, and unsupported file rejection.
- Browser checkbox and view-once send verified in rendered UI; screenshot browser-view-once.jpg.
- Camera service showed no active clients after updated application launch. S21 was locked, so the new viewer's live device check remains pending.
- Lifecycle code confines monitoring to the protected view-once viewer, closes it on leaving the app, and limits each view to two minutes. Ordinary chat and normal attachment previews do not start monitoring.
- No battery consumption measurement or new detection accuracy measurement performed. View-once is access control in this test app; server-held content is not securely erased.

### S21 view-once device check completed

- Ordinary chat displayed “Chat · camera off”; Android camera service had no active clients.
- Opened the synthetic browser-sent view-once message. Protected viewer was visible with masked content and guidance; camera service showed GuardianChat as the active front-camera client.
- After leaving the viewer, camera service had no active clients. This confirms camera lifecycle integration, not detection efficacy or battery measurements.

Attachments now use sanitized original filenames plus a unique ID and file extension in server/data/files. Existing extensionless files are migrated on server startup; API IDs and access rules stay intact. Six backend tests passed, including migration, extension handling and authenticated downloads.

## Viewed-content deletion

Seven backend tests passed. Closing a claimed view deletes its file and clears message text/file metadata for both accounts; expiry performs the same cleanup after interrupted sessions. Server startup sweeps expired/previously closed views. Unopened view-once content is retained until viewed. Android already deletes its viewing cache on close and sweeps media cache on startup; server deletion does not require a new APK. Empty consumed-message records remain to prevent reopening/retry resurrection. External originals/backups and forensic storage recovery are outside this deletion guarantee.

Strict view-once update: shared notice override defaults off; GuardianChat view-once controller disallows temporary override and renders only reposition guidance. Phone risk is posted before awaiting face inference; thresholds and 3 FPS cap unchanged. APK builds and copied SDK/UI unit tests pass. No new timed physical detection benchmark established.

Main GuardianLab SDK defaults now require explicit override opt-in. Main app, SDK sample and integration demo built successfully from a source-identical workspace build copy; 38 SDK and 5 UI tests passed. Main app already dispatches phone threats independently of asynchronous face detection. GuardianChat oxblood/icon/media-preview APK built successfully. Browser image preview and cancel verified in rendered UI, icon checked state verified; oxblood-chat.jpg saved.

Main GuardianLab app, integration demo and SDK sample APKs installed successfully on S21. Their override policy changes were built/tested; live camera accuracy and latency benchmarks remain unmeasured. Browser preview Cancel was verified without sending a message, and view-once icon appears inside the shared composer border.

Figma edits applied: contact card tint/layout, black Send, grey Cancel, rounded view-once controls, message spacing and 24dp screen insets. Clipped Figma contact cards corrected to automatic height. Roboto font files served locally for browser. Android build and 7 backend tests passed; APK installed on S21 and contact text verified in hierarchy. Browser rendered composer visually checked; screenshot design/applied-chat.jpg. Protection logic and deletion behavior were not changed.

Charcoal redesign: Android and browser now use dark neutral backgrounds, white text and oxblood controls. Contacts use compact rows and dividers. Sender and time are italic labels outside content-sized message bubbles. Send has translucent oxblood rounded styling; Android uses RippleDrawable, browser a press light sweep respecting reduced-motion settings. Android build passed and browser screenshot design/charcoal-chat.jpg reviewed.

## Keyboard and compact bubbles — 11 October 2026

Android debug build passed and installed on the S21. Live UI bounds confirmed the composer moves up when the keyboard opens (Send top 1787 → 905 pixels) and returns to 1787 when dismissed. Short message text wraps in a compact bubble with 10 dp horizontal and 6 dp vertical padding; longer text retains wrap-content height and a screen-relative maximum width. Browser bubbles use 6 px vertical / 10 px horizontal padding and automatic height. Browser preview visually checked in design/compact-chat.jpg.

## Personal contacts and inline media preview — 11 October 2026
Eight server tests passed, including empty contact lists, isolation of unrelated accounts, duplicate contact addition, invalid/self codes and rejection of messages before pairing. Existing view-once access/deletion tests passed. Android debug build passed and installed on S21. Device UI confirms personal code, Add person field/button and only paired browser contact. Browser addition and synchronized preview/composer view-once choices verified; preview attached inline, screenshot design/contact-preview.jpg.

S21 media selection also verified: inline preview displayed above the composer with a 32 dp view-once icon and Cancel/Send. Toggling the preview icon enabled both toggles; Cancel dismissed the preview without sending.

## Profiles, unread tracking and typing tools — 11 October 2026
Ten server tests passed, including scoped unread acknowledgements, nickname uniqueness and lookup, stable IDs after profile edits, inaccessible unrelated contact cards and invalid avatar rejection. Existing view-once tests still pass. Android debug build passed. Browser verified contact picture navigation, profile picture compression/save, nickname save, unread badge/divider, disappearance on returning after read, and emoji insertion. Browser notification/speech support depends on the HTTP LAN browser; no audio recording was initiated for the user. Android profile and contact unread badges verified from S21 UI. Startup shield and Android background notification service compiled; actual startup timing, sound audibility and background delivery remain unmeasured on this run.

## Legacy unread correction and badge layout
Found unread records from before the unread-feature rollout. Applied a one-time correction only to that older backlog; the genuinely new 20:09 test message remained unread. Future schema migration initializes legacy messages as read. Eleven tests pass including that migration. Badges now use a 22 dp/px oxblood circle on the right of the contact row. Messages, contact lists and contact cards have outlined boundaries. Android background delivery verified: a new test message produced a high-importance messages-channel notification with number=1 while the app was off-screen. Sound audibility not measured. The connection-service notification is ongoing status, separate from a new-message alert. Read messages cause corresponding service notifications to cancel.

Browser Enter/Shift+Enter verified: Shift+Enter preserved a two-line draft without sending, Enter sent it and cleared the draft. Android message-field editor and hardware-key handlers compiled. S21 right-hand badge displayed 1 and opening its conversation showed the real new notification test message; unread divider correctly increased to 2 when an additional user message arrived. Final width build passed with 8 dp side insets.

Final combined APK installed successfully. S21 UI confirms content bounds moved from x=72–1008 to x=24–1056 on a 1080-pixel screen, matching 8 dp horizontal insets. Android notification permission granted and foreground connection service confirmed running. Browser updated layout screenshot: design/wide-phone-chat.jpg.

## Live unread suppression, sound and receipt circles — 11 October 2026
Twelve server tests pass, including authenticated sent→delivered→read receipts and unrelated-account acknowledgement rejection. Android debug build passed and installed. Browser initial-entry-only unread divider verified with a real incoming test message while the conversation remained open: message displayed, zero unread dividers, delivered/read timestamps set and zero remaining unread. Existing outgoing receipt 44 correctly showed delivered while older read messages showed read. Browser sound now unlocks on click/typing, uses a louder two-tone chime for incoming messages even in the open conversation, and Enable sound plays a test chime. Sound audibility depends on browser/Mac volume and has been asked of the user, not independently measured. Borders added around main and each browser screen.

## Inline media previews
Ordinary images and videos now load as compact previews in browser and Android chat messages. Protected view-once content is excluded. Browser previews verified at 240 × 160 pixels: three images and two videos loaded; full-screen video controls and Back to chat verified. Android build passed; native thumbnail and playback checks still require on-device use. Server tests: all 12 passed. HTTPS is not enabled: a trusted certificate and client account migration are needed before switching the browser origin.

## Inline autoplay and filename strips
Ordinary inline videos autoplay muted when substantially visible, with a bottom-right play/pause button and no protected view-once previews. Browser autoplay and manual pause verified; four long filename strips animate inside bounded single-line labels. Android uses visible-area playback checks and back-and-forth filename scrolling; native visual verification pending.

## Browser playback recovery
Inline autoplay now retries when media becomes playable, the tab becomes visible, or the page regains focus; scroll visibility is recalculated. Manual playback errors are reported instead of silently swallowed. Live browser check: autoplay time advanced from 0.21s to 7.10s; corner pause froze playback at 19.39s, and play resumed to 19.78s. Browser syntax validated. No Android changes in this repair.

## S21 tap-to-preview
Removed the separate Preview button for ordinary image/video messages. Image and video surfaces open the existing full-screen viewer; video corner play/pause remains independent. Nonvisual files retain Open. Android debug build passed.

## Viewer control cleanup
Removed Hide, Retry monitoring, and the duplicate bottom Back to chat button from the Android viewer. The header uses an oxblood chevron with no background box; its invisible touch target remains 44dp for usability. Protected content still uses the GuardianLab cover and existing top/back navigation closes view-once sessions.

## Ash contact rows and 30 MB videos
Contact rows, chat contact header and contact card use ash grey (#555555). Video uploads allow 30 MiB (labelled 30 MB), other attachments remain 8 MiB, enforced in browser, Android and server. JSON body cap accommodates base64 overhead; Android downloads accept up to 30 MiB. All 13 server tests passed, including video above the old limit and rejection of an image of the same size. Android build passed.

## Account sign-in and logout
Salted password sign-in by nickname/ID preserves permanent account ID and history; independent session logout revokes only the current token. Legacy accounts must set password before logout. All 14 server tests passed including wrong-password rejection, account history continuity and account isolation. Browser controls inspected; Android debug build passed. Production HTTPS, account recovery and cloud migration remain outstanding.

## QR cards, profile drafts and Settings
QR PNGs are generated locally using vendored qrcode 8.2 and encode only the stable invitation ID. Contact card panels include picture, nickname, ID and QR; sharing within GuardianChat stages a PNG attachment for review before Send. External sharing omitted after automatic approval review rejection. Picture edits are drafts; Save and Discard appear only on changes. Browser dirty/discard behavior verified. Settings drawer holds notification controls and slides from the right at half width. Android removes Refresh people and refreshes on downward pull at top of chat list.

## Password settings
Password forms moved from profile to Settings in browser and Android. Existing passwords require verification of the current password before replacement; first setup does not. Clients require matching new-password confirmation. All 15 server tests passed, including incorrect/current-password handling and old-password rejection after change. Android build passed.
