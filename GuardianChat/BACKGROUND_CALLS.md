# Background call delivery

The app previously used an always-on local polling service. It remains disabled; there is no permanent connection notification.

Prepared implementation: optional Firebase Cloud Messaging wakes the Android receiver for a ringing call, then the receiver checks the authenticated local call state and displays a ringtone notification. Only opaque call/account identifiers and expiry time go through FCM. Microphone and camera remain off until the user opens and accepts the call. Ended calls cancel the notification. Revoked sessions cannot receive new pushes.

Activation needs a Firebase project and Android app registered as `com.guardianlab.chat`. Put its downloaded Android `google-services.json` at `chat/src/main/assets/firebase-config.json`. The file is ignored by Git. This app initializes Firebase manually from that public Android configuration; Analytics is disabled.

The Mac server also needs the optional `firebase-admin` Python package and a narrowly scoped FCM service-account credential at `server/data/firebase-service-account.json` (ignored by Git, never bundled in the APK). Both Mac and phone need internet access to the push provider. The phone must still reach the local Mac server to verify and answer calls, and the Mac must remain awake.

Without both configurations, background ringing is not active. After activation, grant Android notifications permission and test a call with GuardianChat in the background and the phone locked. Android force-stop prevents delivery until the user reopens the app.

## Local activation

The GuardianChat Firebase project and Android client have been configured locally. The private credential and Android configuration remain excluded from Git. Start the server with `server/.venv-push/bin/python server/server.py` (plus the existing TLS arguments for HTTPS). Recreate that environment with `python3 -m venv server/.venv-push` and `server/.venv-push/bin/python -m pip install -r server/requirements-push.txt`. The Intel Mac dependency constraint uses a compatible prebuilt wheel.

A configured device must open the app once while signed in to register its push token. Keep Android notification permission and Incoming call alerts enabled. Live background ringing still needs an end-to-end call test.

Incoming alerts use Android CallStyle and a full-screen intent. The call screen may appear over the lock screen; chat screens do not. On Android 14 and later, Settings offers an Incoming call screen shortcut to Android’s permission page. Android chooses the banner presentation while unlocked.
