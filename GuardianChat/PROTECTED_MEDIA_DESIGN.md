# Proposed Protected media mode

This is a separate choice from ordinary attachments and View Once. It applies only to new sends; existing messages and stored media are unchanged.

- The message shows an open/download control, with no image, video or audio preview.
- Every opening on Android starts GuardianLab and screenshot blocking. Closing or leaving the app stops the camera.
- Repeated viewing is allowed on the receiving device. Saving, copying and forwarding are disabled in the client and denied by the server.
- Each recipient gets a separate device-bound copy. Android encrypts it with a non-exportable Android Keystore key in private app storage; app backups are disabled. Ordinary file explorers cannot access this storage.
- The server removes its transfer copy only after the app confirms that the encrypted copy has been successfully stored. Transfer failures retain the server copy for retry on the original device.
- A replacement device, app uninstall, or loss of the encryption key cannot recover the protected file. The chat entry remains, marked unavailable on that device.
- Viewing uses a temporary private playback file, deleted on close and cleaned up after interrupted sessions. It is excluded from the clipboard FileProvider and media library.
- Browser accounts may send protected media, but viewing requires Android GuardianLab support.

Activation is pending approval because device binding and removal of the server copy intentionally make recovery impossible. Rooted or compromised devices cannot be given an absolute access guarantee.
