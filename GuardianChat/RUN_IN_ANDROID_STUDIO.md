# Run X ORBIT from Android Studio

This branch applies the Orbit navy, violet and cyan visual theme. Build and device verification results are recorded in ORBIT_THEME_REPORT.md.

## 1. Open the project
1. Install Android Studio and open the **repository root** (the folder with `settings.gradle.kts`), not `GuardianChat/chat`.
2. Let Gradle sync. If it asks for a missing SDK platform or build tools, accept the install.
3. In the run-configuration dropdown choose the **chat** module, not `app` (`app` is the detector app).

## 2. Start the server on your computer
From the `GuardianChat` folder:
- Plain HTTP (simplest): `python3 server/server.py`
- HTTPS (needed for camera and microphone in Orbit Play): see `LOCAL_HTTPS.md`
  `python3 server/server.py --port 8766 --cert server/tls/server.crt --key server/tls/server.key`

The invitation code is printed on start and stored in `server/data/invite.txt`.

## 3. Point the app at the server
The default address is one setting, `DEFAULT_SERVER` in
`GuardianChat/chat/src/main/java/com/guardianlab/chat/ServerConfig.kt`. Change it to your computer's Wi-Fi address, for example `http://192.168.1.50:8765`.
You can also type the address in the app's sign-in screen (the field labelled "Mac address") without rebuilding.

Your phone and computer must be on the same Wi-Fi network.

## 4. Run on a phone
1. On the phone, turn on Developer options and USB debugging, plug it in, and accept the prompt.
2. Choose the phone in the device dropdown and press Run.
3. Sign up with the invitation code, or sign in.

## 5. What to check first
- Intro screen shows the unchanged app icon, a cyan/violet ring and a soft-white X ORBIT title.
- Default chat bubbles: yours cyan with navy text, theirs on a bordered navy surface (pale blue in light mode). Existing saved bubble colour pairs remain selectable.
- Open **Orbit Play** from the chat screen: the wallpaper entry screen, then the existing Play / Compete / Me / Admin groups. Selected tabs are violet with white text; inactive actions use a neutral fill without a blue border. Back arrows have no box.
- Sign in as the admin account (Mainfirst) to see Administration and Admin Studio.

## If the build fails
Copy the first error from the Build tab (the lines starting with `e:`) and send it back. Only visual tokens, fonts, control shapes, focus and motion are changed. Protection, view-once, notification routing and match rules retain their existing workflows.
\nChat follow-up: check the single-line composer (emoji/+ inside, view-once/mic/camera/voice note/Send outside). Tap the camera, allow access if asked, capture a photo, review it and cancel first. A photo must only be sent after pressing Send. Audio has play/pause and seeking without 10-second skips.\n
Version 19 uses the supplied purple/navy dark wallpaper and neon white-line light wallpaper. Switch appearance in chat Settings to check both. Focus the message field: it should keep the single outer pill without an inner typing boundary. Keyboard focus remains visible on other controls.

Version 20 adds the supplied neon launcher icon and light/dark Orbit Play entry icons. The right menu and Settings use the supplied smooth gradients. Check that only OrbitChat/OrbitPlay headings follow the personal colour pair; other labels and inactive buttons retain their normal theme. In the arena, the compact profile is at the top right and its handle is outside the card.
\nVersion 21 replaces the colour dropdown with split-circle choices and a matching wallpaper preview. Dark/Light preview is independent of the app appearance setting. Select confirms the pair; Close abandons an unconfirmed preview. Palette choices remain account-specific. Original artwork files stay unchanged; matching colours are rendered as a display layer.\n

Version 22 moves outgoing file previews into a compact tray attached above the normal message box, capped around 20% of the available chat height. Attach a photo, video, voice note or document; the conversation should remain visible. Type its caption in the normal Message field, then Cancel first: the caption should remain. Attach again and check the tray resizes with the keyboard. Send only when you intend to deliver the file. Check both the main Send button and forwarding options, and verify view-once/protected choices remain mutually exclusive. A received attachment should still open in its existing viewer.
