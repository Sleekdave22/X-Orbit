# Account search, navigation and wallpaper — 21 October 2026

Repository: Sleekdave22/X-Orbit, branch fix/separate-android-installer.
Extends selected release 2f984d7. No merge into main.

## Delivered

- Android version 7 retains com.guardianlab.chat and the existing @s21 account,
  notification configuration and protected-file keys. Chats, Calls and Search
  now sit below the list. Selecting the already selected tab does nothing.
- Both clients show the approved app icon followed by “Orbit Play”. Copyright
  X ORBIT © lives at the bottom of Settings, outside the native scrolling controls.
- Authenticated GET /social/search?q=…&offset=… searches public, discoverable names
  and nicknames, or exact account IDs/nicknames. Private/non-discoverable accounts
  are returned only for exact identifiers. Blocks in either direction exclude
  accounts. Responses contain only existing public card fields and contact status.
- Pages contain at most 20 accounts. Parameterized queries escape wildcard input.
  Search never grants contact or chat access. New connections use existing message
  requests and require the recipient’s acceptance. Browser results open public
  profiles; native results offer an existing chat or a message request.
- Clients reject stale search responses after edits, account changes or navigation.
  Browser search results clear on sign-out/account change. Search remains directly
  usable and is not folded into the optional form panels.
- The owner-supplied Maroon Gold Doodle Wallpaper PNG is copied unchanged into
  browser branding and native drawable-nodpi assets. Desktop repeats a bounded-width
  pattern; native scales with preserved aspect ratio and caches a shared bitmap.
  Light mode uses a pale scrim. Cards and protected viewer covers remain readable.
- Restored aliases from legacy chat CSS variables to the approved theme tokens,
  preventing white buttons becoming unreadable against a light background.

## Files and storage

MainActivity.kt, OrbitWallpaper.kt, chat/build.gradle.kts and native wallpaper;
server index.html, account-search.js, social.py, server.py, orbit-theme.css,
browser wallpaper and account-search tests. No schema migration or data reset.
Existing icons, logos, GuardianLab engine and latest-message layout class unchanged.

## Validation actually completed

- 35 Python tests passed: account search, existing social features, Phase B and
  sponsored league contracts. New search tests cover auth, private/discovery rules,
  bidirectional blocks, literal wildcard handling, bounds and pagination.
- JavaScript search checks passed: stale and other-account responses, account
  reset, profile opening and retrying failed pagination. Existing call-refresh and
  profile/presence/browser-script checks passed.
- Android unit tests: 4 passed; debug build succeeded after wallpaper integration.
- Isolated browser fixture with 24 synthetic accounts: search, exact nickname,
  pagination, public profile opening, copyright placement and theme switching
  verified. Tab rectangle stayed at y=619, height=69 while switching panels.
  Narrow search panel has no horizontal overflow. Wallpaper visually inspected.
- Live HTTPS page, script and wallpaper match source bytes; authenticated account
  search works; SQLite integrity is OK. Runtime backup retained 5 accounts and
  165 messages. Version 7 installation succeeded; existing @s21 API session verified.

Native visual confirmation is requested from the owner because automated native
screen controls are unavailable in this session. Build and installation success
do not substitute for that visual check.

## Ranking and league scope

Game-specific Elo, verified global results and the separate sponsored league
lifecycle, points, standings, disputes and appeals are implemented and tested.
This does not mean every historical handoff is complete. Command Center roles/MFA,
large-pool load testing and pagination, controlled corrections of finalized results,
stable hosted networking and remaining end-to-end live/background checks remain
recorded in APPROVED_IMPLEMENTATION_QUEUE.md. Real-money features remain disabled.

## Manual checks

Refresh https://localhost:8766/ and reopen the S21 app. Check bottom tabs, search an
exact @nickname, open a profile or request a new conversation, inspect Settings’
footer, switch appearance and open an existing chat at the latest message. Native
localhost continues to require the existing ADB reverse connection in this setup.
