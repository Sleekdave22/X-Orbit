# Background call delivery

The app previously used an always-on local polling service. It remains disabled; there is no permanent connection notification.

Prepared implementation: optional Firebase Cloud Messaging wakes the Android receiver for a ringing call, then the receiver checks the authenticated local call state and displays a ringtone notification. Only opaque call/account identifiers and expiry time go through FCM. Microphone and camera remain off until the user opens and accepts the call. Ended calls cancel the notification. Revoked sessions cannot receive new pushes.

Activation needs a Firebase project and Android app registered as `com.guardianlab.chat`. Put its downloaded Android `google-services.json` at `chat/src/main/assets/firebase-config.json`. The file is ignored by Git. This app initializes Firebase manually from that public Android configuration; Analytics is disabled.

The Mac server also needs the optional `firebase-admin` Python package and a narrowly scoped FCM service-account credential at `server/data/firebase-service-account.json` (ignored by Git, never bundled in the APK). Both Mac and phone need internet access to the push provider. The phone must still reach the local Mac server to verify and answer calls, and the Mac must remain awake.

Without both configurations, background ringing is not active. After activation, grant Android notifications permission and test a call with GuardianChat in the background and the phone locked. Android force-stop prevents delivery until the user reopens the app.
