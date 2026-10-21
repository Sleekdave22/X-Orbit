# Chat navigation, colour and profile-photo update

21 October 2026. Branch: fix/separate-android-installer, following 2957759.

## Delivered

- Outside conversations, the main search bar and top magnifier use authenticated
  global account search. Search does not add people or grant conversation access.
- Inside a conversation, the top-right magnifier searches its loaded history by
  text or ordinary attachment name. History loading includes all pages. View Once,
  protected and deleted message bodies are excluded. Selecting a result jumps to
  it; the native latest-message anchor yields only for that explicit search jump.
- A three-line button opens an animated menu with the existing profile, Settings
  and Orbit Play destinations. The profile is no longer in the main header.
  Settings contents are retained pending the owner's forthcoming specification.
- Bottom navigation contains Calls and Search. Chats is the default home screen;
  Back returns from Calls/Search. Existing latest-message opening remains intact.
- General surfaces and default controls are quieter ash colours; received bubbles
  are dark with cream text, and outgoing bubbles are gold with dark text.
- View Once uses a vector “1”, broken orbital ring and glint. The checkbox/toggle,
  spoken label and protection behavior remain unchanged. Wallpaper, approved app
  icon and GuardianLab engine are preserved.
- Android profile avatars now use ImageDecoder instead of BitmapFactory so legacy
  EXIF orientation is respected in thumbnails, enlarged photos, search results,
  profile editing and contact-card sharing. Upload normalization is retained.

## Existing S21 photograph

The stored @s21 photo was visually sideways and had orientation=1, so metadata-aware
decoding alone could not fix it. A one-time, compare-and-swap maintenance repair
turned that account's existing image upright, saved losslessly as PNG and incremented
profile_version. The original and rollback fields were backed up outside Git. No
other profile, account session, competitive record or protected file was changed.
No personal photo or private backup is included in this commit.

## Verification

- Android debug assembly and four existing native unit checks passed after the
  final navigation/icon changes. Canonical package remains com.guardianlab.chat,
  versionCode 8, versionName 0.8-x-orbit-chat-navigation.
- Existing JavaScript checks passed: profile/presence and browser syntax, account
  search races, call refresh, voice-note waveform/playback, forwarding and View Once.
- Five Python tests passed: profile-image orientation/validation and account search.
- Isolated browser fixture: global lookup from the main search bar, menu expansion,
  Calls→Back navigation and absence of the bottom Chats button verified. A
  conversation with 126 messages loads past the 100-message page boundary. Searching
  “needle” finds the first ordinary message while excluding a View Once message
  containing that same word. Selecting the result settles at scrollTop=0. Gold sent
  and dark received bubbles, wallpaper and icon layout were visually inspected.
- Browser update uses existing static routes, requiring no server restart or schema
  migration. Existing shared server and accounts remain in use. The new Wi-Fi ADB
  endpoint was rediscovered and localhost forwarding restored for the S21.

## Manual phone check

Reopen X_ORBIT. Check the top menu and magnifier, then open menu → profile and verify
the photograph is upright. Open a conversation, search for an older ordinary
message, and return to the latest messages. Check View Once is still clearly
labelled and toggles correctly. Native visual confirmation is separate from build
and installation verification because native UI automation is unavailable here.
