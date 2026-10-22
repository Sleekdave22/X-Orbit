"""Metadata-only message pushes; previews require the recipient's live session."""
import threading
import time
import social


def preview(server, uid, message_id):
    with server.db() as db:
        row = db.execute('SELECT m.*,u.name AS sender_name FROM messages m JOIN users u ON u.id=m.sender WHERE m.id=? AND m.recipient=? AND m.deleted_all=0 AND m.read_at=0 AND m.kind<>? AND m.id NOT IN (SELECT message_id FROM message_hidden WHERE user_id=?)',
                         (message_id, uid, 'call', uid)).fetchone()
        if not row or social.blocked(db, uid, row['sender']):
            raise LookupError('Message unavailable')
        text = ('Protected media' if row['protected_media'] else 'View-once content' if row['view_once']
                else row['text'] or row['filename'] or 'Attachment')
        return {'id': row['id'], 'peer': row['sender'], 'name': row['sender_name'],
                'preview': text[:400], 'time': row['time']}


def dispatch(server, message_id):
    if not server.push.enabled:
        return
    with server.db() as db:
        row = db.execute('SELECT recipient FROM messages WHERE id=?', (message_id,)).fetchone()
        if not row:
            return
        uid = row['recipient']
        devices = [r['token'] for r in db.execute('SELECT p.token FROM push_devices p JOIN sessions s ON s.token_hash=p.session_hash AND s.user_id=p.user_id WHERE p.user_id=?', (uid,))]

    def deliver():
        # No text, attachment names, credentials or protected content go through FCM.
        for token in devices:
            try:
                preview(server, uid, message_id)
                server.push.send(token, {'event': 'chat_message', 'recipient': uid,
                                         'message_id': str(message_id), 'expires_at': str(int(time.time()) + 600)})
            except LookupError:
                return
            except Exception as error:
                print('Message push failed: ' + type(error).__name__, flush=True)
    threading.Thread(target=deliver, daemon=True).start()
