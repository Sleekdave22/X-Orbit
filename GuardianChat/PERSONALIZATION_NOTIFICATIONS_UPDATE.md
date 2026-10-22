# Account appearance and background message notifications

Selected application: `com.guardianlab.chat`, X_ORBIT version 9 (`0.9-x-orbit-personalization-notifications`).
Repository: `Sleekdave22/X-Orbit`, branch `fix/separate-android-installer`.
Base reviewed against GitHub: `1e5374d92e3ebf50404f144027ed1ca80f67a4ca`.

## Changes

- Use the supplied black/gold space doodle wallpaper in native Android and browser pages, preserving its aspect ratio. Browser wide screens repeat the image at a bounded width. Logos, launcher icon and GuardianLab protection are unchanged.
- Settings → Personalization offers six coordinated colour choices. A saved choice controls outgoing message bubbles and selected/action buttons in chat and Orbit Play, per account. Inactive controls remain neutral. Received messages remain dark.
- The shared, authenticated `/preferences` GET/POST contract saves only an allowed palette ID. The additive `account_preferences` table does not modify accounts, results, ratings or financial records. Browser responses and native callbacks are scoped to the current account/session; caches use account-specific keys.
- Both clients have Chats and Calls bottom tabs. Global account search remains accessible outside conversations. The in-chat magnifier sits immediately left of the far-right menu control.
- Navigation opens as a right-side drawer at 30% viewport width. The profile photo sits left of the name, followed by a separator and Settings. The browser respects reduced-motion preferences.
- Native sending explicitly returns the conversation to the latest message, including optimistic sending and attachments/forwarding. Existing initial-chat bottom anchoring remains.

## Notification repair

The previous native FCM handler supported calls and game updates, while saved chat messages did not dispatch pushes. Message alerts therefore stopped when the application was no longer visible.

New messages and forwarded messages now dispatch a high-priority `chat_message` push after the database commit. The push contains recipient/message IDs and an expiry, not message text, filenames, credentials or protected content. Devices must still belong to active sessions. Retried sends with the same client ID do not generate another push.

Android retrieves the preview over authenticated HTTPS through `/messages/notification?id=…`. This endpoint is recipient-only and excludes read, hidden, deleted and blocked-account messages. It does not mark messages read. View Once and protected messages return generic descriptions. Android notifications use private lock-screen visibility and include an account-scoped, unique destination for the exact message. Tapping opens and highlights that message, including on a cold start; unavailable destinations fall back to the conversation. Duplicate/out-of-order pushes are suppressed per account and sender.

Message notification registration no longer depends solely on whether incoming call alerts are enabled. Existing notification opt-outs remain respected.

## Validation and limits

- Android debug build and existing JVM unit checks passed.
- Backend integration checks cover push dispatch after commit, recipient/session permissions, private previews, duplicate sends, forwards, read/block/logout exclusions, preference validation and account isolation. Preset text contrast is tested.
- Browser regression checks cover existing notification de-duplication, Calls refresh and account-search races. New tests cover stale account colour responses, logout and session changes. Inline browser scripts parse successfully.
- Synthetic browser verification confirmed 30% drawer width, Chats/Calls navigation, successful colour saving, coloured outgoing bubbles, matching Orbit Play selected-button colour and the new wallpaper.
- Real-device background receipt and exact-message tapping require live verification on the S21 after installation. They are not claimed as end-to-end verified by a successful build.
- This remains a local HTTPS test installation. The server must be reachable by the phone to retrieve previews. Android force-stop, disabled notifications, network loss or OS restrictions can prevent delivery; the app cannot override these conditions.
- Deployment preserves runtime data and credentials and uses a database/file backup. No merge to main or real-money features are part of this update.
