# Same-Wi-Fi voice calling: first test version

Open a contact chat and tap the telephone icon. Both participants must use the same Wi-Fi and keep GuardianChat open. The browser requires trusted HTTPS. Android uses a dedicated WebView call screen with microphone-only permission and the shared browser WebRTC engine. On Android, open an incoming call and then press Accept on the call screen; acceptance is explicit. Mute, enable audio and end controls are available. Audio uses the current device output; dedicated Bluetooth/output selection is not implemented.

Voice calls never request the camera. Microphone tracks and the connection stop on hang-up, background transitions or failure. Opening a voice call closes view-once content. Calls are not recorded or saved as media.

Signalling is authenticated and participant-scoped. Only added contacts may be called; overlapping calls involving either participant are rejected. Unanswered calls expire after 45 seconds; active calls expire after a participant stops polling for 35 seconds. SDP is cleared on termination and ended entries are pruned after 60 seconds. Signalling is in memory, so server restart ends calls. This prototype uses local host ICE candidates with no external STUN/TURN service.

Not included: video, internet relay, closed-app incoming-call push, call history, dedicated Bluetooth routing or group calls. Real microphone and speaker output still need a two-device test. Automated tests cover authorization, busy rules, expiry, audio-only capture, mute, hang-up and cancellation.

Checks: run python3 -m unittest test_server.py and node test_calls.js in server/.

Press feedback uses a transparent sweep in the browser and translucent touch ripples on Android clickable controls.
