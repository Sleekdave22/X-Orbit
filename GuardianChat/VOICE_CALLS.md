# Same-Wi-Fi audio and video calling: test version

Open a contact chat and tap the handset icon for audio or the camera icon for video. Both participants must use the same Wi-Fi and keep GuardianChat open. The browser requires trusted HTTPS. Android uses a dedicated WebView call screen with microphone permission for audio and camera plus microphone permission for video and the shared browser WebRTC engine. Incoming calls open the call screen. Press the green Accept button to answer; camera and microphone are not requested for incoming calls until explicit acceptance. Mute, enable audio and end controls are available. Android has a built-in speaker/earpiece toggle. The browser offers audio-output selection only when supported; it does not claim to control a mobile browser earpiece. Dedicated Bluetooth routing is not implemented.

Voice calls never request the camera. Microphone tracks and the connection stop on hang-up, background transitions or failure. Opening a voice call closes view-once content. Calls are not recorded or saved as media.

Signalling is authenticated and participant-scoped. Only added contacts may be called; overlapping calls involving either participant are rejected. Unanswered calls expire after 45 seconds; active calls expire after a participant stops polling for 35 seconds. SDP is cleared on termination and ended entries are pruned after 60 seconds. Signalling is in memory, so server restart ends calls. This prototype uses local host ICE candidates with no external STUN/TURN service.

Not included: internet relay, closed-app incoming-call push, dedicated Bluetooth routing or group calls. Real microphone and speaker output still need a two-device test. Automated tests cover authorization, busy rules, expiry, audio-only capture, mute, hang-up and cancellation.

Checks: run python3 -m unittest test_server.py and node test_calls.js in server/.

Press feedback uses a transparent sweep in the browser and translucent touch ripples on Android clickable controls.

The full call screen shows the peer profile photo, a timer starting at WebRTC connection establishment, green Accept at lower left and red End at lower right with edge spacing. The Chats/Calls home toggle shows account-scoped call history persisted in the existing private SQLite database, including direction, outcome, start time and connected duration. History begins with this update; audio and SDP are not written into history. Repeated connected notifications do not reset the start time. The timer stops on hang-up. Additional timer and speaker-control checks: node test_call_screen.js.

The persistent Android Wi-Fi connection service has been disabled at the user’s request. Calls and message alerts work while the app is open; reliable closed-app delivery is unavailable until server-backed push notifications are implemented. No ongoing connection notification is shown.

Call controls use plain coloured handset icons. Completed call screens show the frozen connected duration, blink it six times over three seconds, and return to the conversation. The timer is hidden before connection. Incoming, outgoing and missed audio calls appear in account-scoped call history and chat timelines; the chat list shows the latest call description. Video calls preserve their type in history and chat events.

The Media library opens from a contact profile and lists only regular sent and received attachments in that conversation without copying their contents. View-once entries are excluded by the server query. Profile pictures open in a centred circular viewer that closes when tapped outside; names still open the contact profile. Wide browser screens keep the contact list on the left, with a dark oxblood highlight on the open conversation.

The media library offers a list with file previews and separators, plus a gallery with three or five columns. It is no longer a home-page tab. Only visible previews load; library videos remain paused. The browser library uses the small oxblood back arrow at the top left.

Video calls default to modest 640×480 capture at 15 fps, capped at 1280×720 and 24 fps. The screen shows remote video and a small local preview, with camera off/on and front/back switching. Camera-off stops the local video track rather than merely hiding its preview. Video calls use speaker output by default on Android. All capture tracks stop on hang-up or leaving the call. Live video still needs a two-device acceptance test; automated checks cover media constraints, explicit answer flow, camera off/on/flip and cleanup.

Regular media can be forwarded from the library or a message menu to any added contact, including the original conversation. Long-press offers Forward, Save, Copy and Delete for me. Swipe-right selects a reply above the composer; sent messages include a short quote. View-once quote previews contain only a generic label and cannot be forwarded or copied. Swipe-left offers confirmed deletion for messages and chats, affecting only the current account. Deleted chats reappear when new messages arrive; existing deleted history remains hidden. Pasted clipboard files/images open in the attachment preview before sending. Browser image copying uses PNG clipboard support where available; other copied media can be pasted back within the app.

Video calls now fill the screen. The local preview starts at the bottom left and supports pointer/touch dragging, edge collapse and an edge arrow to restore it. The Hide arrow collapses toward the nearest edge. Hiding the self-preview changes only its display; the call continues.

Regular voice notes play directly within chat bubbles, with waveform amplitudes decoded from the actual audio and a seekable timeline. Only one inline voice note plays at a time; playback pauses when the app is backgrounded and releases on navigation. The browser handles audio with an unknown WebM duration using the decoded duration when available.

Hold the voice-note icon to record. Release to stop and preview, or drag upward to lock and then tap Stop. Recording shows elapsed time and live microphone amplitude. Playback uses frame-rate playhead updates; Android defers seeking until the drag ends so the thumb is not reset by stale decoder positions. Browser recording prefers AAC-in-MP4 explicitly or Opus-in-WebM/Ogg, avoiding Opus-in-MP4 compatibility problems. View Once resets after successful sending.

Forwarding selects a destination and opens the ordinary attachment preview, with View Once available before the explicit Send action. Sender-only Delete for everyone clears the shared server payload and removes file access, while leaving a deletion placeholder. Open chat clients receive deletion IDs and replace visible content; open viewers close after their next status poll. Copies saved or forwarded earlier are separate and are not recalled. Long-press menus use compact ash actions with touch feedback and reset swipe displacement before opening.
