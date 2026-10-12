#!/usr/bin/env python3
"""Private LAN testing only. No E2EE. Do not expose this HTTP server publicly."""
import argparse, base64, hashlib, hmac, json, os, re, mimetypes, secrets, sqlite3, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import sys, zlib, struct, ssl, threading
sys.path.insert(0,str(Path(__file__).parent/"vendor"))
import qrcode
from functools import lru_cache
@lru_cache(maxsize=1024)
def account_qr(uid):
    qr=qrcode.QRCode(box_size=6,border=4);qr.add_data(uid);qr.make(fit=True);matrix=qr.get_matrix();scale=6;width=len(matrix)*scale
    raw=b"".join(b"\x00"+bytes(0 if cell else 255 for cell in row for _ in range(scale)) for row in matrix for _ in range(scale))
    def chunk(kind,data):return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,width,8,0,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")
    return base64.b64encode(png).decode()
MAX_FILE = 8 * 1024 * 1024
MAX_VIDEO = 30 * 1024 * 1024
MAX_BODY = 41 * 1024 * 1024
class ChatServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, data):
        self.data=Path(data); self.data.mkdir(parents=True,exist_ok=True); self.data.chmod(0o700)
        (self.data/'files').mkdir(exist_ok=True)
        code=self.data/'invite.txt'
        if not code.exists(): code.write_text(secrets.token_urlsafe(12));code.chmod(0o600)
        self.invite=code.read_text().strip()
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender TEXT NOT NULL,recipient TEXT NOT NULL,text TEXT NOT NULL,filename TEXT,mime TEXT,fileid TEXT,size INTEGER,time INTEGER,client_id TEXT NOT NULL,UNIQUE(sender,client_id));''')
            user_columns={r[1] for r in db.execute('PRAGMA table_info(users)')}
            for name,kind in [('password_hash',"TEXT DEFAULT ''"),('nickname','TEXT'),('profile_version','INTEGER DEFAULT 0'),('avatar',"TEXT DEFAULT ''"),('avatar_mime',"TEXT DEFAULT ''")]:
                if name not in user_columns:db.execute(f'ALTER TABLE users ADD COLUMN {name} {kind}')
            db.execute('UPDATE users SET nickname=id WHERE nickname IS NULL')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_nickname ON users(nickname COLLATE NOCASE)')
            columns={r[1] for r in db.execute('PRAGMA table_info(messages)')}
            for name,kind in [('delivered_at','INTEGER DEFAULT 0'),('read_at','INTEGER DEFAULT 0'),('view_once','INTEGER DEFAULT 0'),('opened','INTEGER DEFAULT 0'),('lease_hash','TEXT'),('lease_until','INTEGER')]:
                if name not in columns:
                    db.execute(f'ALTER TABLE messages ADD COLUMN {name} {kind}')
                    if name=='read_at':db.execute('UPDATE messages SET read_at=?',(int(time.time()),))
        with self.db() as db:db.execute('CREATE TABLE IF NOT EXISTS contacts(owner TEXT NOT NULL,peer TEXT NOT NULL,PRIMARY KEY(owner,peer))')
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO sessions SELECT token_hash,id FROM users')
        with self.db() as db:
            db.execute('CREATE INDEX IF NOT EXISTS messages_participants_id ON messages(sender,recipient,id)')
            db.execute('CREATE INDEX IF NOT EXISTS messages_unread ON messages(recipient,read_at,sender)')
            db.execute('CREATE INDEX IF NOT EXISTS messages_undelivered ON messages(recipient,delivered_at,id)')
        self.calls={};self.call_lock=threading.RLock()
        self.login_attempts={}
        self.migrate_files()
        self.expire_views()
        super().__init__(address,Handler)
    def expire_calls(self):
        now=time.time()
        for key,call in list(self.calls.items()):
            if call['state']=='ended':
                if now-call['ended_at']>60:del self.calls[key]
            elif (call['state']=='ringing' and now-call['created']>45) or now-min(call['seen'].values())>35 and call['state']=='active':
                call.update(state='ended',reason='No answer' if call['state']=='ringing' else 'Connection lost',ended_at=now,offer=None,answer=None)
    def call_view(self,call,uid):
        peer=call['recipient'] if uid==call['caller'] else call['caller']
        with self.db() as db:row=db.execute('SELECT name FROM users WHERE id=?',(peer,)).fetchone()
        return {k:call.get(k) for k in ('id','caller','recipient','state','offer','answer','reason')}|{'peer':peer,'peer_name':row['name'] if row else 'Contact'}
    def db(self):
        db=sqlite3.connect(self.data/'chat.sqlite',timeout=15);db.row_factory=sqlite3.Row;db.execute('PRAGMA secure_delete=ON');return db
    def delete_view(self, db, row):
        if row['fileid']:
            self.file_path(row['fileid'],row['filename'],row['mime']).unlink(missing_ok=True)
            (self.data/'files'/row['fileid']).unlink(missing_ok=True)
        db.execute("UPDATE messages SET text='',filename=NULL,mime=NULL,fileid=NULL,size=0,lease_hash=NULL,lease_until=NULL WHERE id=?",(row['id'],))
    def expire_views(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute('SELECT * FROM messages WHERE view_once=1 AND opened=1 AND (lease_until IS NULL OR lease_until<=?)',(int(time.time()),)).fetchall()
            for row in rows:self.delete_view(db,row)
    def service_actions(self):
        self.expire_views()
    def file_path(self, fid, filename, mime):
        # Keep a readable basename, with a unique ID so duplicate names never overwrite.
        name=str(filename or 'attachment').replace('\\','/').split('/')[-1]
        name=re.sub(r'[^\w. ()-]', '_', name).strip(' .')[:150] or 'attachment'
        suffix=Path(name).suffix
        if not suffix:
            suffix={ 'image/jpeg':'.jpg', 'image/png':'.png', 'audio/wav':'.wav',
                     'text/plain':'.txt' }.get(mime) or mimetypes.guess_extension(mime or '') or ''
        stem=Path(name).stem if Path(name).suffix else name
        return self.data/'files'/f'{stem}__{fid}{suffix}'
    def migrate_files(self):
        with self.db() as db:
            for row in db.execute('SELECT fileid,filename,mime FROM messages WHERE fileid IS NOT NULL'):
                old=self.data/'files'/row['fileid']
                target=self.file_path(row['fileid'],row['filename'],row['mime'])
                if old.is_file() and not target.exists():old.rename(target)
class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args): pass # No message bodies, credentials or IDs in access logs.
    def reply(self,status,obj):
        data=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def user(self):
        token=self.headers.get('Authorization','').removeprefix('Bearer ')
        with self.server.db() as db: row=db.execute('SELECT user_id AS id FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row: raise PermissionError('Please connect again')
        return row['id']
    def do_GET(self):
        try:
            parsed=urlparse(self.path)
            if parsed.path in ('/calls.js','/call.html'):
                data=(Path(__file__).parent/parsed.path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript' if parsed.path.endswith('.js') else 'text/html');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if parsed.path=='/guardianchat-ca.crt':
                data=(Path(__file__).parent.parent/'chat/src/main/res/raw/guardianchat_local_ca.crt').read_bytes();self.send_response(200);self.send_header('Content-Type','application/x-x509-ca-cert');self.send_header('Content-Disposition','attachment; filename=guardianchat-ca.crt');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if parsed.path in ('/roboto-0.ttf','/roboto-1.ttf'):
                data=(Path(__file__).parent/parsed.path[1:]).read_bytes()
                self.send_response(200);self.send_header('Content-Type','font/ttf');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if parsed.path=='/':
                data=(Path(__file__).parent/'index.html').read_bytes()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
            uid=self.user()
            if parsed.path=='/calls':
                with self.server.call_lock:
                    self.server.expire_calls();calls=[]
                    for call in self.server.calls.values():
                        if uid in (call['caller'],call['recipient']):
                            call['seen'][uid]=time.time();calls.append(self.server.call_view(call,uid))
                    self.reply(200,{'calls':calls});return
            with self.server.db() as db:
                if parsed.path=='/profile':
                    target=parse_qs(parsed.query).get('id',[uid])[0]
                    if target!=uid and not db.execute('SELECT 1 FROM contacts WHERE owner=? AND peer=?',(uid,target)).fetchone():self.reply(404,{'error':'Profile unavailable'});return
                    row=db.execute('SELECT id,name,nickname,avatar,avatar_mime,profile_version FROM users WHERE id=?',(target,)).fetchone()
                    if not row:self.reply(404,{'error':'Profile unavailable'});return
                    profile=dict(row);
                    if target==uid:profile['has_password']=bool(db.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()['password_hash'])
                    profile['qr_png']=account_qr(target);self.reply(200,profile);return
                if parsed.path=='/users':
                    self.reply(200,{'users':[dict(r) for r in db.execute('SELECT u.id,u.name,u.nickname,u.profile_version,(SELECT COUNT(*) FROM messages m WHERE m.sender=u.id AND m.recipient=c.owner AND m.read_at=0) unread,(SELECT COALESCE(MAX(id),0) FROM messages m WHERE m.sender=u.id AND m.recipient=c.owner) latest FROM users u JOIN contacts c ON c.peer=u.id WHERE c.owner=? ORDER BY u.name',(uid,))]});return
                if parsed.path=='/inbox':
                    self.reply(200,{'ids':[r['id'] for r in db.execute('SELECT id FROM messages WHERE recipient=? AND delivered_at=0 ORDER BY id LIMIT 500',(uid,))]});return
                if parsed.path=='/receipts':
                    peer=parse_qs(parsed.query).get('peer',[''])[0]
                    self.reply(200,{'receipts':[dict(r) for r in db.execute('SELECT id,client_id,delivered_at,read_at FROM messages WHERE sender=? AND recipient=? ORDER BY id DESC LIMIT 1000',(uid,peer))]});return
                if parsed.path=='/messages':
                    q=parse_qs(parsed.query);peer=q.get('peer',[''])[0];after=int(q.get('after',['0'])[0])
                    rows=db.execute('SELECT * FROM messages WHERE id>? AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?)) ORDER BY id LIMIT 100',(after,uid,peer,peer,uid))
                    items=[]
                    for r in rows:
                        item=dict(r);item.pop('lease_hash',None);item.pop('lease_until',None)
                        if item['view_once']:item.update(text='',filename='View-once content',mime='',fileid=None,size=0)
                        items.append(item)
                    unread=db.execute('SELECT COUNT(*) FROM messages WHERE sender=? AND recipient=? AND read_at=0',(peer,uid)).fetchone()[0]
                    self.reply(200,{'messages':items,'unread_count':unread});return
                if parsed.path.startswith('/files/'):
                    fid=parsed.path.split('/')[-1]
                    row=db.execute('SELECT * FROM messages WHERE fileid=? AND (sender=? OR recipient=?)',(fid,uid,uid)).fetchone()
                    if not row: self.reply(404,{'error':'File not available'});return
                    if row['view_once']:
                        lease=self.headers.get('X-View-Token','')
                        valid=uid==row['recipient'] and row['lease_until'] and row['lease_until']>=time.time() and hmac.compare_digest(hashlib.sha256(lease.encode()).hexdigest(),row['lease_hash'] or '')
                        if not valid:self.reply(403,{'error':'View-once session unavailable'});return
                    p=self.server.file_path(fid,row['filename'],row['mime'])
                    if not p.is_file(): self.reply(404,{'error':'File not available'});return
                    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(p.stat().st_size));self.send_header('Cache-Control','no-store');self.end_headers()
                    with p.open('rb') as f:
                        while chunk:=f.read(65536):self.wfile.write(chunk)
                    return
            self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except (ValueError,KeyError):self.reply(400,{'error':'Invalid request'})
        except (BrokenPipeError,ConnectionResetError):pass
    def do_POST(self):
        try:
            self.connection.settimeout(20)
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>MAX_BODY:self.reply(413,{'error':'Videos must be 30 MB or smaller; other attachments 8 MB or smaller'});self.close_connection=True;return
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise ValueError()
            if self.path=='/login':
                key=self.client_address[0];attempts,until=self.server.login_attempts.get(key,(0,0))
                if attempts>=8 and until>time.time():self.reply(429,{'error':'Too many attempts. Try again in one minute.'});return
                identity=str(body.get('identity','')).strip().lstrip('@');password=str(body.get('password',''))
                with self.server.db() as db:
                    row=db.execute('SELECT * FROM users WHERE id=? OR nickname=? COLLATE NOCASE',(identity,identity)).fetchone()
                    stored=row['password_hash'] if row else ''
                    salt=stored.split(':')[0] if stored else '0'*32
                    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000).hex()
                    if not stored or not hmac.compare_digest(stored,salt+':'+digest):
                        self.server.login_attempts[key]=(attempts+1 if until>time.time() else 1,time.time()+60);raise PermissionError('Incorrect account or password')
                    token=secrets.token_urlsafe(32);db.execute('INSERT INTO sessions VALUES(?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id']))
                    self.server.login_attempts.pop(key,None)
                    self.reply(200,{'id':row['id'],'name':row['name'],'nickname':row['nickname'],'token':token});return
            if self.path=='/register':
                if not hmac.compare_digest(str(body.get('invite','')),self.server.invite):raise PermissionError('Incorrect invitation code')
                name=str(body.get('name','')).strip()
                if not 1<=len(name)<=40:raise ValueError()
                uid=uuid.uuid4().hex[:12];token=secrets.token_urlsafe(32)
                nickname=str(body.get('nickname') or uid).strip().lstrip('@').lower()
                if not re.fullmatch(r'[a-z0-9_]{3,24}',nickname):self.reply(400,{'error':'Nickname must be 3–24 letters, numbers or underscores'});return
                with self.server.db() as db:
                    if db.execute('SELECT 1 FROM users WHERE nickname=? COLLATE NOCASE',(nickname,)).fetchone():self.reply(409,{'error':'That nickname is already taken'});return
                    db.execute('INSERT INTO users(id,name,token_hash,nickname) VALUES(?,?,?,?)',(uid,name,hashlib.sha256(token.encode()).hexdigest(),nickname))
                with self.server.db() as db:db.execute('INSERT INTO sessions VALUES(?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid))
                self.reply(201,{'id':uid,'token':token,'name':name,'nickname':nickname});return
            uid=self.user()
            if self.path.startswith('/calls/'):
                with self.server.call_lock:
                    self.server.expire_calls()
                    if self.path=='/calls/start':
                        peer=str(body.get('peer',''));offer=body.get('offer',{})
                        if not isinstance(offer,dict) or offer.get('type')!='offer' or not isinstance(offer.get('sdp'),str) or not 1<=len(offer['sdp'])<=65536:raise ValueError('Invalid offer')
                        with self.server.db() as db:
                            if not db.execute('SELECT 1 FROM contacts WHERE owner=? AND peer=?',(uid,peer)).fetchone():raise PermissionError('Add this contact first')
                        if any(c['state']!='ended' and (uid in (c['caller'],c['recipient']) or peer in (c['caller'],c['recipient'])) for c in self.server.calls.values()):self.reply(409,{'error':'You or this contact are already in a call'});return
                        key=uuid.uuid4().hex;now=time.time();call={'id':key,'caller':uid,'recipient':peer,'state':'ringing','offer':offer,'answer':None,'created':now,'seen':{uid:now,peer:now}};self.server.calls[key]=call;self.reply(201,self.server.call_view(call,uid));return
                    call=self.server.calls.get(str(body.get('id','')))
                    if not call or uid not in (call['caller'],call['recipient']):raise PermissionError('Call unavailable')
                    if self.path=='/calls/answer':
                        answer=body.get('answer',{})
                        if uid!=call['recipient'] or call['state']!='ringing':raise PermissionError('Call cannot be answered')
                        if not isinstance(answer,dict) or answer.get('type')!='answer' or not isinstance(answer.get('sdp'),str) or not 1<=len(answer['sdp'])<=65536:raise ValueError('Invalid answer')
                        call.update(state='active',answer=answer);call['seen'][uid]=time.time()
                    elif self.path=='/calls/end':call.update(state='ended',reason='Call ended',ended_at=time.time(),offer=None,answer=None)
                    else:self.reply(404,{'error':'Not found'});return
                    self.reply(200,self.server.call_view(call,uid));return
            if self.path=='/password':
                password=str(body.get('password',''))
                if not 10<=len(password)<=128:self.reply(400,{'error':'Use a password of 10–128 characters'});return
                with self.server.db() as db:
                    old=db.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()['password_hash']
                    if old:
                        current=str(body.get('current_password',''))
                        if not 1<=len(current)<=128:raise PermissionError('Confirm your current password first')
                        old_salt=old.split(':')[0];actual=hashlib.pbkdf2_hmac('sha256',current.encode(),bytes.fromhex(old_salt),200000).hex()
                        if not hmac.compare_digest(old,old_salt+':'+actual):raise PermissionError('Current password is incorrect')
                    salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000).hex()
                    db.execute('UPDATE users SET password_hash=? WHERE id=?',(salt+':'+digest,uid))
                self.reply(200,{'saved':True});return
            if self.path=='/logout':
                token_hash=hashlib.sha256(self.headers.get('Authorization','').removeprefix('Bearer ').encode()).hexdigest()
                with self.server.db() as db:
                    if not db.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()['password_hash']:self.reply(409,{'error':'Set your sign-in password before logging out'});return
                    db.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash,))
                    db.execute('UPDATE users SET token_hash=? WHERE id=? AND token_hash=?',(secrets.token_hex(32),uid,token_hash))
                self.reply(200,{'logged_out':True});return
            if self.path=='/profile':
                with self.server.db() as db:
                    old=db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
                    name=str(body.get('name',old['name'])).strip();nickname=str(body.get('nickname',old['nickname'])).strip().lstrip('@').lower()
                    if not 1<=len(name)<=40 or not re.fullmatch(r'[a-z0-9_]{3,24}',nickname):self.reply(400,{'error':'Use a name and a 3–24 character nickname'});return
                    if db.execute('SELECT 1 FROM users WHERE nickname=? COLLATE NOCASE AND id<>?',(nickname,uid)).fetchone():self.reply(409,{'error':'That nickname is already taken'});return
                    avatar=old['avatar'];mime=old['avatar_mime']
                    if 'avatar' in body:
                        raw=base64.b64decode(body['avatar'],validate=True);mime=str(body.get('avatar_mime',''))
                        if len(raw)>256*1024 or not ((mime=='image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (mime=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n'))):self.reply(400,{'error':'Choose a JPEG or PNG profile picture under 256 KB'});return
                        avatar=body['avatar']
                    db.execute('UPDATE users SET name=?,nickname=?,avatar=?,avatar_mime=?,profile_version=profile_version+1 WHERE id=?',(name,nickname,avatar,mime,uid))
                self.reply(200,{'id':uid,'name':name,'nickname':nickname});return
            if self.path=='/delivered':
                ids=body.get('ids',[])
                if not isinstance(ids,list) or not 1<=len(ids)<=500:raise ValueError()
                with self.server.db() as db:
                    for mid in ids:db.execute('UPDATE messages SET delivered_at=? WHERE id=? AND recipient=? AND delivered_at=0',(int(time.time()),int(mid),uid))
                self.reply(200,{'delivered':True});return
            if self.path=='/read':
                with self.server.db() as db:db.execute('UPDATE messages SET read_at=?,delivered_at=CASE WHEN delivered_at=0 THEN ? ELSE delivered_at END WHERE recipient=? AND sender=? AND id<=?',(int(time.time()),int(time.time()),uid,str(body['peer']),int(body['through'])))
                self.reply(200,{'read':True});return
            if self.path=='/contacts':
                code=str(body.get('code','')).strip().lower().replace('-','');lookup=code.lstrip('@')
                with self.server.db() as db:
                    other=db.execute('SELECT id,name FROM users WHERE id=? OR nickname=? COLLATE NOCASE',(code,lookup)).fetchone()
                    if not other or other['id']==uid:self.reply(400,{'error':'Enter another person’s valid contact code'});return
                    code=other['id']
                    db.execute('INSERT OR IGNORE INTO contacts VALUES(?,?)',(uid,code))
                    db.execute('INSERT OR IGNORE INTO contacts VALUES(?,?)',(code,uid))
                self.reply(200,{'contact':dict(other)});return
            if self.path in ('/open','/close'):
                with self.server.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row=db.execute('SELECT * FROM messages WHERE id=? AND recipient=? AND view_once=1',(int(body['message_id']),uid)).fetchone()
                    if not row:self.reply(404,{'error':'Content unavailable'});return
                    if self.path=='/close':
                        if not row['opened']:self.reply(409,{'error':'Content has not been opened'});return
                        self.server.delete_view(db,row)
                        self.reply(200,{'closed':True});return
                    if row['opened']:self.reply(409,{'error':'This view-once content has already been opened'});return
                    lease=secrets.token_urlsafe(32)
                    db.execute("UPDATE messages SET delivered_at=CASE WHEN delivered_at=0 THEN CAST(strftime('%s','now') AS INTEGER) ELSE delivered_at END,read_at=CAST(strftime('%s','now') AS INTEGER),opened=1,lease_hash=?,lease_until=? WHERE id=?",(hashlib.sha256(lease.encode()).hexdigest(),int(time.time())+120,row['id']))
                    item=dict(row);item.pop('lease_hash',None);item.pop('lease_until',None);item['view_token']=lease;item['opened']=1
                self.reply(200,item);return
            if self.path!='/messages':self.reply(404,{'error':'Not found'});return
            peer=str(body['peer']);text=str(body.get('text','')).strip();client=str(body['client_id'])
            if len(text)>4000 or not 1<=len(client)<=80:raise ValueError()
            with self.server.db() as db:
                if not db.execute('SELECT 1 FROM contacts WHERE owner=? AND peer=?',(uid,peer)).fetchone():self.reply(403,{'error':'Add this person using their contact code first'});return
                existing=db.execute('SELECT id FROM messages WHERE sender=? AND client_id=?',(uid,client)).fetchone()
                if existing:self.reply(200,{'id':existing['id']});return
                data=None;fid=None;filename=None;mime=None
                if body.get('data'):
                    data=base64.b64decode(body['data'],validate=True)
                    limit=MAX_VIDEO if str(body.get('mime','')).startswith('video/') else MAX_FILE
                    if len(data)>limit:self.reply(413,{'error':'Videos must be 30 MB or smaller; other attachments 8 MB or smaller'});return
                    filename=str(body.get('filename','attachment')).replace('\\','/').split('/')[-1][:150]
                    mime=str(body.get('mime','application/octet-stream'))[:100]
                    fid=uuid.uuid4().hex
                if not text and not data:raise ValueError()
                once=bool(body.get('view_once',False))
                if once and data and not (mime.startswith(('image/','video/','audio/','text/')) or mime=='application/pdf'):
                    self.reply(400,{'error':'View once supports messages, images, video, audio, text and PDF previews'});return
                if data:self.server.file_path(fid,filename,mime).write_bytes(data)
                try:
                    cur=db.execute('INSERT INTO messages(sender,recipient,text,filename,mime,fileid,size,time,client_id,view_once) VALUES(?,?,?,?,?,?,?,?,?,?)',(uid,peer,text,filename,mime,fid,len(data) if data else 0,int(time.time()*1000),client,int(once)))
                    msgid=cur.lastrowid
                except Exception:
                    if fid:self.server.file_path(fid,filename,mime).unlink(missing_ok=True)
                    raise
            self.reply(201,{'id':msgid})
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except (ValueError,KeyError,TypeError):self.reply(400,{'error':'Invalid message or attachment'})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:self.reply(500,{'error':'Server could not save this message'})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='0.0.0.0');p.add_argument('--port',type=int,default=8765);p.add_argument('--data',default=str(Path(__file__).parent/'data'));p.add_argument('--cert');p.add_argument('--key');a=p.parse_args();
    if bool(a.cert)!=bool(a.key):p.error('Supply both --cert and --key')
    s=ChatServer((a.host,a.port),a.data)
    if a.cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(a.cert,a.key);s.socket=context.wrap_socket(s.socket,server_side=True)
    print(f'GuardianChat LAN server on port {a.port}. Invitation code is in {s.data / "invite.txt"}. Use test content only.',flush=True)
    s.serve_forever()
