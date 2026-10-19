# Run X ORBIT from Android Studio

This repo was redesigned in the oxblood and gold style. The Android changes have not been compiled by the person who wrote them, so the first build is also the first test.

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
- Intro screen shows the app icon and a gold X ORBIT title.
- Chat bubbles: yours oxblood, theirs on a bordered surface.
- Open **Orbit Play** from the chat screen: the new entry screen, then the tabs grouped Play / Compete / Me / Admin.
- Sign in as the admin account (Mainfirst) to see Administration and Admin Studio.

## If the build fails
Copy the first error from the Build tab (the lines starting with `e:`) and send it back. The Android edits were small: default colours and the intro screen in `chat/.../MainActivity.kt`.
