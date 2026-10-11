# Local HTTPS testing

Address: https://192.168.1.171:8766/

The HTTPS listener uses the existing server/data database and uploads. The HTTP listener is retained temporarily while test devices are configured. Android upgrades the known local address and rejects cleartext connections; its network security configuration trusts this local CA only for the configured test hosts. Never disable certificate or hostname verification.

Start from the project directory:

    python3 server/server.py --port 8766 --cert server/tls/server.crt --key server/tls/server.key

Private TLS keys remain in ignored server/tls; never commit them. Public CA certificate: chat/src/main/res/raw/guardianchat_local_ca.crt. Server certificate expires after 90 days; CA after 365. If the Mac IP changes, issue a new server certificate with that IP and update the Android domain configuration.

Mac: open the public CA certificate in Keychain Access, add it to the login keychain, then open the certificate, expand Trust and set SSL to Always Trust. Approve with your Mac credentials. Trust only your own GuardianChat test CA.

iPhone: download the public CA from http://192.168.1.171:8765/guardianchat-ca.crt, install it through Settings > General > VPN & Device Management, then enable it under Settings > General > About > Certificate Trust Settings. Open the HTTPS address in Safari.

HTTPS is a different browser origin, so sign in again using the same existing account and password. Chats and contacts remain in the same database. If an account has no password, set it from the existing HTTP session before moving. Notification permission must be requested again on the HTTPS origin. HTTPS does not add end-to-end encryption or offline push notifications.
