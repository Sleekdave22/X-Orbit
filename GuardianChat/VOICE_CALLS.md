# Same-Wi-Fi voice calling: first test version

Open a contact chat and tap the telephone icon. Both participants must use the same Wi-Fi and keep GuardianChat open. The browser requires trusted HTTPS. Android uses a dedicated WebView call screen with microphone-only permission and the shared browser WebRTC engine. Incoming calls open the call screen. Press the green Accept button to answer; the microphone is not requested until explicit acceptance. Mute, enable audio and end controls are available. Android has a built-in speaker/earpiece toggle. The browser offers audio-output selection only when supported; it does not claim to control a mobile browser earpiece. Dedicated Bluetooth routing is not implemented.

Voice calls never request the camera. Microphone tracks and the connection stop on hang-up, background transitions or failure. Opening a voice call closes view-once content. Calls are not recorded or saved as media.

Signalling is authenticated and participant-scoped. Only added contacts may be called; overlapping calls involving either participant are rejected. Unanswered calls expire after 45 seconds; active calls expire after a participant stops polling for 35 seconds. SDP is cleared on termination and ended entries are pruned after 60 seconds. Signalling is in memory, so server restart ends calls. This prototype uses local host ICE candidates with no external STUN/TURN service.

Not included: video, internet relay, closed-app incoming-call push, dedicated Bluetooth routing or group calls. Real microphone and speaker output still need a two-device test. Automated tests cover authorization, busy rules, expiry, audio-only capture, mute, hang-up and cancellation.

Checks: run python3 -m unittest test_server.py and node test_calls.js in server/.

Press feedback uses a transparent sweep in the browser and translucent touch ripples on Android clickable controls.

The full call screen shows the peer profile photo, a timer starting at WebRTC connection establishment, green Accept at lower left and red End at lower right with edge spacing. The Chats/Calls home toggle shows account-scoped call history persisted in the existing private SQLite database, including direction, outcome, start time and connected duration. History begins with this update; audio and SDP are not written into history. Repeated connected notifications do not reset the start time. The timer stops on hang-up. Additional timer and speaker-control checks: node test_call_screen.js.

Incoming Android calls now ring through a private high-priority call notification when the UI is closed, while the foreground Wi-Fi connection service is running. Notification permission and Incoming calls in Settings must be enabled. Opening the notification validates the live, account-scoped call, displays the incoming screen and still requires explicit Accept before microphone capture. Decline authenticates the end request. Ringing stops when the call ends or expires. Closing an unanswered incoming screen hands ringing to the background listener; accepted calls still end on leaving the app in this test version. Force-stop, reboot without reopening, loss of Wi-Fi, notification/DND settings and Android background-service limits can prevent delivery. This is local testing, not guaranteed always-on push delivery.

Call controls use plain coloured handset icons. Completed call screens show the frozen connected duration, blink it six times over three seconds, and return to the conversation. The timer is hidden before connection. Incoming, outgoing and missed audio calls appear in account-scoped call history and chat timelines; the chat list shows the latest call description. Video calling remains unimplemented.

The Media library opens from a contact profile and lists only regular sent and received attachments in that conversation without copying their contents. View-once entries are excluded by the server query. Profile pictures open in a centred circular viewer that closes when tapped outside; names still open the contact profile. Wide browser screens keep the contact list on the left, with a dark oxblood highlight on the open conversation.

The media library offers a list with file previews and separators, plus a gallery with three or five columns. It is no longer a home-page tab. Only visible previews load; library videos remain paused. The browser library uses the small oxblood back arrow at the top left.
