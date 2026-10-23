# X ORBIT visual update report
23 October 2026

## Header, settings gradients and supplied icons — version 20
The owner's neon trophy/chat artwork is now the launcher icon and the default web app icon. Its light counterpart is used by the Orbit Play entry/header icon in light mode; dark mode uses the neon artwork. Original PNG bytes are retained. One density-independent launcher resource replaces the old density-specific icons; the package identity and manifest are unchanged.

The OrbitChat top strip and its search/menu button fills are transparent. The right navigation drawer and Settings use the supplied Deep Purple to Midnight image in dark mode and Lavender to Cyan image in light mode. Both are packaged for Android; three exact public branding paths are added to the server's existing static image allowlist. They contain only the supplied artwork. Existing protection, authentication and API rules are unchanged.

Personalization now supplies heading-dark/heading-light variables only to the OrbitChat heading and the arena's OrbitPlay heading. The native chat title reads the same account palette fields. Other text, buttons, ratings, standings and interaction handlers retain the fixed app theme. Preference requests still ignore stale accounts/sessions and reset on logout. A regression assertion checks the heading values without introducing a global personal accent.

The arena's compact contact card sits at the top right, with its public handle on a separate line outside the card and the names inside. Opening the card still opens the same profile dialog; full profile details retain their existing information.

Actual checks: Android debug build passed; 5 chat unit tests passed; 22 browser regression checks passed; 78 defined contrast pairs passed. APK inspection confirmed both settings backgrounds, the light icon and final interface assets. Trusted HTTPS returned exact deployed bytes for the updated assets. Managed-browser review confirmed transparent chat/header controls, both settings gradients and icon variants, the separate handle/right-aligned card, and no horizontal overflow at the reviewed 680px and 1280px widths. The requested 390px viewport override did not take effect in the managed review tab and was reset; no successful 390px review is claimed. Physical phone visual/camera walkthroughs remain owner checks.

Version 20 was installed over the existing handset package without resetting its account. Package metadata and authenticated profile, league and match API checks passed. The browser server was restarted after an integrity-checked database backup; existing accounts/data and TLS material were retained. Earlier wallpaper/control work was separately committed as 85c5c70.

## Wallpaper and control refinement — version 19
The two newly supplied wallpapers replace only the previous wallpaper assets: Purple-to-Navy Tech Doodle for dark mode, Neon White-Line Tech Travel Doodle for light mode. The source PNG bytes are copied unchanged into web and Android assets. The native renderer centre-crops without stretching; the web layout uses cover on small screens and repeats proportional 560px-wide artwork on wider screens. Chat reading surfaces and the gaming content area have a translucent theme surface for text contrast; the composer has a quiet solid surface for its bare icons. Live video remains unobscured.

Inactive buttons now use the same raised neutral fill and muted text as Calls, without blue borders. Primary actions and selected tabs retain their violet fill. Back arrows have transparent backgrounds and borders, with their existing tap targets and handlers. Only the chat draft loses its inner focus outline; typing, caret, selection and keyboard focus on other controls remain available.

Both wallpapers are also included in the optional bundled WebView interface through its exact, same-origin static-asset allowlist. No API, media, authentication or TLS allowlist rules are broadened. Existing wallpaper routes are reused, so the live browser receives the new assets without a server restart.

Validation: 22 browser regression checks passed; 78 defined contrast pairs passed. Trusted HTTPS returned exactly the updated CSS, scripts and both PNGs. Managed-browser review confirmed dark/light wallpaper selection, a focused draft with no outline or shadow, a bare Back control, transparent borders on inactive gaming tabs and no horizontal overflow in the reviewed layout. The new static-asset test also rejects foreign origins, traversal and unknown image paths. These checks do not certify contrast on every wallpaper pixel or all custom themes. The phone visual walkthrough remains an owner check.

## Slim composer — version 18
The message field is tagged as chat-draft so the generic theme refresh no longer paints a solid rectangular EditText background over the rounded composer. Only the outer pill supplies the fill, clipped to its outline. Normal bar height is 38dp/px with a 36dp/px text area; multiline input remains available. Composer glyphs are 18dp/px, view-once 20dp/px and the Send circle 36dp/px. Compact icon widths are 28dp/px, widening to 36 on larger layouts. This supersedes the earlier 32/44px dimensions below. The native voice-note icon also keeps its smaller size after recording ends.

## S21 chat header — version 17
The chat header now matches the browser hierarchy: the upper bar has Orbit Chat, search and menu; a separate contact row has Back, the 40dp picture, an 18sp single-line name with ellipsis, presence and the voice/video actions. Call glyphs are 20dp inside 44dp targets; end padding keeps them away from the edge. The identity has a flexible width rather than competing with all five navigation actions in one row.

The temporary localhost:8898 preview was an isolated test database in a fixed 390px iframe. Demo Owner had test-only admin rights; the synthetic sample contact was the synthetic contact in its chat. Read-only verification found no demo IDs or the synthetic sample contact account in the real database; the designated owner account was the sole game-admin account. The preview tab and test server were closed.

The Android build and 4 chat tests passed, and all 22 browser checks passed. Version 17 is prepared for/installed through the existing S21 installation flow; the final phone walkthrough remains an owner check.

## Compact composer and camera — version 16
The final arrangement follows the owner's latest correction: emoji and + sit inside the message field on the left; view-once, dictation mic, camera, voice-note waveform and Send sit outside on the right, all on one line. Native/mobile icons use compact 32px/dp-wide, 44px/dp-high hit regions so the message field keeps space; the Send circle is 40px/dp. Wider web screens use 40px icon widths. This intentionally supersedes the earlier separate toolbar described below.

The camera is a new, explicitly requested function. Android opens the system camera using the existing scoped FileProvider and its existing CAMERA permission, normalizes photo orientation and opens the existing preview/send flow. Browser camera capture uses a local video preview, stops tracks on close/navigation/incoming calls and stages the captured photo in the existing attachment preview. Neither camera path automatically uploads or sends the photo. Cancelling discards the native temporary capture. Account/peer checks prevent a delayed capture from being staged in another conversation.

Validation: the Android build and 4 chat unit tests passed; all 22 browser checks passed, including the new camera permission/cancel/stale-context and late-result tests. Browser layout was visually inspected at the normal viewport and in an isolated 390px frame; the one-line composer fits. Actual hardware photo capture and the new S21 visual arrangement still require the owner's walkthrough. Version 16 is installed; the existing the existing handset account account and direct Wi-Fi endpoint remain in use.

## Chat corrections — version 15
The owner's follow-up changes are now included:
- Sent default bubbles match the Orbit Play violet button, with white text. Received default bubbles use blue #202546 (light-mode equivalent #E8EDF6). The stable palette ID remains orbit-cyan-navy for account compatibility; its displayed name is Orbit violet / Blue.
- Voice notes use blue/cyan waveform, play glyph and playhead accents. Their 10-second backward/forward buttons are removed in the inline and full audio viewer; play/pause and timeline seeking remain. Video skip controls remain.
- Native call actions use centred 44dp image targets and explicit cyan tint, with a rounded camera symbol and header edge padding.
- Emoji, attachment, dictation, view-once and recording controls have bare backgrounds and separate 44px/dp targets. A second composer row gives them space; a flexible gap separates recording from Send.
- The S21 was saved against localhost after its ADB reverse route disappeared. The route was restored and the saved server changed to the already trusted direct Wi-Fi endpoint, the existing trusted Wi-Fi endpoint. The matching CA, endpoint response and existing the existing handset account session were verified. Credentials/account data were retained.
- the existing handset account had Blue / Gold saved, while the owner account had Red / Sky blue. Both accounts were switched through the existing preference service/UI to the requested violet/blue pair.

Follow-up checks: Android debug build and 4 chat unit tests passed; all 21 browser regression checks passed; 3 account-preference tests passed; 78 text/control/voice-wave contrast pairs passed. The previous full-suite legacy rating-test limitation below is unchanged. Managed-browser review confirmed purple/blue bubbles, cyan call icons and the spaced bare composer. A new phone visual walkthrough still needs owner confirmation; installation and saved account/API checks passed.

## Delivered
The selected Compare interface in Sleekdave22/X-Orbit now uses the supplied navy, violet and cyan theme. Chat, Orbit Play, calls, settings, profiles, forms and Admin Studio share the new colours, bundled Sora headings and Inter body type, rounded cards and buttons, visible focus states and reduced-motion support.

Repository: Sleekdave22/X-Orbit. Review branch: style/orbit-navy-violet-cyan. Base: fix/separate-android-installer at 582c42b. This base keeps the review focused on styling rather than including earlier, already functioning application work. Main is not merged or changed.

Version 19 replaced only the wallpapers at the owner’s explicit request. Version 20 additionally replaces the app/launcher icon with the supplied neon artwork and adds its light counterpart for Orbit Play. Logos remain unchanged. Entry pages continue to show the app icon in the existing ring.

## Implemented colours
| Role | Dark | Light |
|---|---|---|
| Screen | #0B1520 | #F4F7FB |
| Card | #131932 | #FFFFFF |
| Raised surface / received default bubble | #202546 | #E8EDF6 |
| Decorative border | #2E3560 | #C5CEE0 |
| Main text | #F1F5F9 | #0B1520 |
| Secondary text | #94A3B8 | #4A5878 |
| Primary action fill, white text | #7C3AED | #6D28D9 |
| Violet text | #A78BFA | #6D28D9 |
| Cyan text / outline | #22D3EE | #0E7490 |
| Own default bubble, white text | #7C3AED | #6D28D9 |
| Send button, navy text | #22D3EE | #22D3EE |
| Success | #34D399 | #047857 |
| Warning fill, navy text | #FFB822 | #FFB822 |
| Warning text | #FFB822 | #8A5A00 |
| Error / loss | #FF7185 | #BE123C |
| Strong control edge | #64759A | #78859F |

Cards use 16px corners, buttons 12px, and main controls at least 44px/dp. Light controls use a stronger edge than the handoff example: its suggested #8793AE failed the 3:1 target on raised surfaces. The implemented #78859F passes at 3.16:1. Medals retain gold, silver and bronze.

Existing account-specific message colour choices remain available to preserve functionality and saved preferences; version 20 also applies their heading shades to the two brand headings. Orbit violet / Blue is the new default; Charcoal / Black is also available. Consequently, old colour literals remain intentionally in the optional personal palette catalogue, exact legacy-default migration and related regression fixtures. They are not the fixed application chrome. Existing admin custom theme values are not overwritten. Version 19 uses the newly supplied dark/light wallpaper artwork, as described above.

## Changes by area
- Web: orbit-theme.css supplies shared tokens, embedded offline WOFF2 fonts and visual overrides. Related chat, gaming, profile and call styles use matching role colours. Entry markup and rank/contact-card drawing use the new visual language.
- Android: OrbitPalette.kt centralizes dark/light tokens. MainActivity's existing visual helpers, intro, bubble rendering, system bars, wallpaper renderer and small vector tints use them. Sora/Inter TTF files and font licences are included. Package identity stays com.guardianlab.chat.
- Protection UI: only panel/text/button colours changed in GuardianProtection.kt and ProtectionNotice.kt. Protection and view-once logic are unchanged.
- Server: only the presentation default and its exact-match migration changed in gamebox_core.py; account_preferences.py changes the default personal palette ID. The migration preserves the exact theme key set, custom themes, policy values and unpublished drafts.
- Documentation/tests: Android Studio instructions, presentation assertions, two integration migration tests and contrast evidence.

The separate app/ShieldController.kt and second app theme file listed in the handoff do not exist in this selected repository. No files were invented or changed in the original GuardianLab repository.

## Functional boundaries
Apart from the explicitly requested camera capture and removed audio skip controls described above, this change does not implement or alter ratings, league rules, matchmaking, payments, result verification, moderation permissions, message routing, notification links, capture/protection rules or account data. Existing handlers, registration gates, Play / Compete / Me / Admin grouping, streaming overlays and navigation are retained.

## Actual verification
| Check | Result |
|---|---|
| Android debug build | Passed: :chat:assembleDebug |
| Android unit tests | Passed: 5 chat tests; previous 5 guardianlab-ui tests unchanged |
| Browser JavaScript regression checks | 22 of 22 passed |
| Backend unittest discovery | 192 run: 179 passed, 13 errors |
| Legacy-error baseline | Same 13 errors reproduced against unchanged gamebox_core.py from 582c42b |
| Theme migration integration tests | Passed: exact old default, custom preservation and repeat startup |
| Contrast script | 78 pairs, zero failures |
| Diff whitespace check | Passed |
| Artwork / manifest | Only explicitly supplied wallpapers and icons changed; logos and manifest unchanged |
| Installed S21 package | versionCode 20, 0.20-x-orbit-personal-headings |
| Existing S21 account | the existing handset account retained; authenticated profile, leagues and match APIs respond |
| Live browser assets | Trusted HTTPS returns the exact updated CSS, gaming entry and 11-choice catalogue |

The 13 server errors are in legacy test_rating.py, which expects removed helpers such as apply_rating, rating_change, rating_tier and tier_bounds, plus old configuration keys. They predate this visual change. They were not hidden or “fixed” by changing current competitive behaviour.

Contrast evidence lists every checked pair in artifacts/orbit-theme/CONTRAST.md and contrast.json. Text pairs meet 4.5:1; tested control edges meet 3:1. These measurements verify the defined pairs, not every possible video frame or administrator-defined custom colour.

## Visual review and limits
Managed-browser inline review covered mobile dark chat, Orbit Play home, registration and global rankings; desktop light Orbit Play and Admin Studio; and the deployed chat list. Forms, navigation and dialogs opened during that review.

The requested complete 390px/1280px × dark/light screenshot matrix is not complete. The isolated Playwright browser aborted at launch under the sandbox; the managed-browser screenshot-file write was also denied. Inline screenshots were inspected, but no saved screenshot set is claimed. Calls, every league table state and every settings panel therefore still need final visual review. The S21 installation and account were verified through package/API checks; a new on-device visual walkthrough has not been supplied by the owner.

Unlike the handoff's cloud assumption, this Mac has Android Studio: the Android build and tests were actually run and passed.

## Deployment
The browser now runs the selected X-Orbit source at https://localhost:8766/ with the existing database and TLS configuration. The database was backed up before restart. Original GuardianLab source was not overwritten. Version 20 was installed over the existing S21 app without uninstalling it. No accounts were reset and no real-money feature was enabled.

## Owner check
1. Refresh https://localhost:8766/ and reopen X_ORBIT on the S21.
2. Check dark/light mode, a chat's own/received bubbles, Calls and Settings.
3. Open Orbit Play: inspect registration, rankings, a league table and Admin Studio.
4. Check existing personal bubble colour selections remain selectable.
5. Confirm the app icon, notifications and protected/view-once actions still behave as expected.

GitHub review contains this visual-only change; deployment is a local test update, not a production-readiness claim.
