# Received message tint and expanded colours

X_ORBIT version 10 (`0.10-x-orbit-expanded-colours`).

Received-message surfaces on Android and the browser now blend 30% of approved oxblood `#6A1833` into the former `#1D1A1C` surface, giving `#341923` after sRGB rounding. Existing text, bubble dimensions, wallpaper and outgoing-message choices are preserved.

Personalization now offers 14 account-specific choices. Added combinations: Crimson & gold, Royal blue & gold, Navy & coral, Crimson & sky blue, Emerald & gold, Teal & amber, Amethyst & gold, and Cobalt & lemon. Existing palette IDs and saved account selections remain valid.

Validation: preset contrast/account isolation tests and the stale-account browser regression passed. All preset bubble/text pairs and white text on action colours meet the tested 4.5:1 minimum. The Android debug build and existing JVM tests passed.
