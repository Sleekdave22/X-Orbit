# Account storage and future migration

The permanent users.id identifies each account. Nicknames are editable lookup names and do not replace that ID. Messages belong to their sender and recipient IDs, contacts to their owner ID; attachment access requires authentication as a message participant. View-once leases remain recipient-specific.

Data lives in server/data/chat.sqlite and server/data/files on the Mac. Move both together to retain accounts, profiles, contacts and chat history. Use SQLite’s backup API while the server is running, or stop it before copying. Do not copy the active SQLite file alone. Cloud migration must preserve IDs and file IDs, configure trusted HTTPS and clients, and handle browser account/session migration to the new origin. No cloud deployment has been performed.

Accounts set or change passwords in Settings while authenticated; replacing a saved password requires the current password. Passwords are salted PBKDF2-SHA256 hashes with 200,000 iterations. Login accepts nickname or ID and opens another session; logout revokes the current session only. Logout is blocked until a password exists. No password reset or recovery flow yet; keep your password safe. This is a local HTTP prototype: use a test password, not one reused elsewhere.

Android logout clears account metadata and generated media caches, disables notifications and returns to sign-in. Browser logout clears its stored session and visible account content. Server chat history stays tied to the account.
