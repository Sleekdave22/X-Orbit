"""Phase B: TEST VALUE ONLY. No provider, deposits, withdrawals or entry-fee endpoints."""
import hashlib,hmac,json,re,secrets,time,uuid
CURRENCY='NGN'
MAX_AMOUNT=1_000_000             # 10,000 test NGN per transfer
DAILY_LIMIT=5_000_000            # rolling 24 hours, test value only
MAX_BALANCE=1_000_000_000_000

def init(server):
 with server.db() as d:
  d.executescript('''
  CREATE TABLE IF NOT EXISTS fin_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS fin_wallets(id TEXT PRIMARY KEY,owner TEXT NOT NULL UNIQUE,currency TEXT NOT NULL CHECK(currency='NGN'),status TEXT NOT NULL CHECK(status IN ('active_test','restricted')),created INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS fin_accounts(id TEXT PRIMARY KEY,wallet TEXT,kind TEXT NOT NULL CHECK(kind IN ('available','reserved','test_treasury')),normal INTEGER NOT NULL CHECK(normal IN (-1,1)),UNIQUE(wallet,kind));
  CREATE TABLE IF NOT EXISTS fin_journals(id TEXT PRIMARY KEY,kind TEXT NOT NULL,actor TEXT NOT NULL,reference TEXT NOT NULL UNIQUE,created INTEGER NOT NULL,posted INTEGER NOT NULL DEFAULT 0 CHECK(posted IN (0,1)),description TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS fin_postings(journal TEXT NOT NULL,account TEXT NOT NULL,amount INTEGER NOT NULL CHECK(typeof(amount)='integer' AND amount!=0 AND abs(amount)<=1000000000000),PRIMARY KEY(journal,account));
  CREATE TABLE IF NOT EXISTS fin_operations(actor TEXT NOT NULL,key TEXT NOT NULL,fingerprint TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(actor,key));
  CREATE TABLE IF NOT EXISTS fin_quotes(id TEXT PRIMARY KEY,actor TEXT NOT NULL,recipient TEXT NOT NULL,amount INTEGER NOT NULL,expires INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS fin_holds(id TEXT PRIMARY KEY,owner TEXT NOT NULL,amount INTEGER NOT NULL,reference TEXT NOT NULL UNIQUE,expires INTEGER NOT NULL,state TEXT NOT NULL CHECK(state IN ('reserved','released')),created INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS fin_permissions(owner TEXT NOT NULL,capability TEXT NOT NULL CHECK(capability='overview'),PRIMARY KEY(owner,capability));
  CREATE TABLE IF NOT EXISTS fin_rate(owner TEXT,action TEXT,bucket INTEGER,count INTEGER NOT NULL,PRIMARY KEY(owner,action,bucket));
  CREATE TABLE IF NOT EXISTS fin_outbox(id INTEGER PRIMARY KEY,owner TEXT NOT NULL,journal TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(owner,journal));
  CREATE TABLE IF NOT EXISTS fin_audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,reference TEXT NOT NULL,created INTEGER NOT NULL);
  CREATE INDEX IF NOT EXISTS fin_posting_account ON fin_postings(account,journal);
  CREATE INDEX IF NOT EXISTS fin_journal_actor ON fin_journals(actor,created);
  CREATE TRIGGER IF NOT EXISTS fin_journal_draft BEFORE INSERT ON fin_journals WHEN NEW.posted!=0 BEGIN SELECT RAISE(ABORT,'Journals must begin as drafts'); END;
  CREATE TRIGGER IF NOT EXISTS fin_posting_insert BEFORE INSERT ON fin_postings BEGIN
   SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM fin_journals WHERE id=NEW.journal AND posted=0) OR NOT EXISTS(SELECT 1 FROM fin_accounts WHERE id=NEW.account) THEN RAISE(ABORT,'Invalid draft or account') END;
  END;
  CREATE TRIGGER IF NOT EXISTS fin_posting_no_update BEFORE UPDATE ON fin_postings BEGIN SELECT RAISE(ABORT,'Postings are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_posting_no_delete BEFORE DELETE ON fin_postings BEGIN SELECT RAISE(ABORT,'Postings are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_journal_seal BEFORE UPDATE ON fin_journals BEGIN
   SELECT CASE WHEN OLD.posted!=0 OR NEW.posted!=1 OR NEW.id!=OLD.id OR NEW.kind!=OLD.kind OR NEW.actor!=OLD.actor OR NEW.reference!=OLD.reference OR NEW.created!=OLD.created OR NEW.description!=OLD.description OR (SELECT COUNT(*) FROM fin_postings WHERE journal=OLD.id)<2 OR (SELECT COALESCE(SUM(amount),1) FROM fin_postings WHERE journal=OLD.id)!=0 THEN RAISE(ABORT,'Unbalanced or immutable journal') END;
  END;
  CREATE TRIGGER IF NOT EXISTS fin_journal_no_delete BEFORE DELETE ON fin_journals BEGIN SELECT RAISE(ABORT,'Journals are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_account_no_update BEFORE UPDATE ON fin_accounts BEGIN SELECT RAISE(ABORT,'Ledger accounts are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_account_no_delete BEFORE DELETE ON fin_accounts BEGIN SELECT RAISE(ABORT,'Ledger accounts are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_wallet_owner BEFORE UPDATE ON fin_wallets WHEN NEW.id!=OLD.id OR NEW.owner!=OLD.owner OR NEW.currency!=OLD.currency OR NEW.created!=OLD.created BEGIN SELECT RAISE(ABORT,'Wallet ownership is immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_wallet_no_delete BEFORE DELETE ON fin_wallets BEGIN SELECT RAISE(ABORT,'Wallet history must be retained'); END;
  CREATE TRIGGER IF NOT EXISTS fin_audit_no_update BEFORE UPDATE ON fin_audit BEGIN SELECT RAISE(ABORT,'Audit history is immutable'); END;
  CREATE TRIGGER IF NOT EXISTS fin_audit_no_delete BEFORE DELETE ON fin_audit BEGIN SELECT RAISE(ABORT,'Audit history is immutable'); END;
  ''')
  d.execute("INSERT OR IGNORE INTO fin_accounts VALUES('test-treasury',NULL,'test_treasury',1)")
  for user in d.execute('SELECT id FROM users').fetchall():create_wallet(d,user['id'])
  # Existing authorised administrator gets reporting only, never a spending/minting role.
  if not d.execute("SELECT 1 FROM fin_meta WHERE key='overview_bootstrap'").fetchone():
   d.execute("INSERT OR IGNORE INTO fin_permissions SELECT uid,'overview' FROM game_admin")
   d.execute("INSERT INTO fin_meta VALUES('overview_bootstrap','completed')")

def create_wallet(d,uid):
 if not d.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise ValueError('Account not found')
 d.execute("INSERT OR IGNORE INTO fin_wallets VALUES(?,?,'NGN','active_test',?)",(uuid.uuid4().hex,uid,int(time.time())))
 w=dict(d.execute('SELECT * FROM fin_wallets WHERE owner=?',(uid,)).fetchone())
 for kind in ('available','reserved'):d.execute('INSERT OR IGNORE INTO fin_accounts VALUES(?,?,?,-1)',(w['id']+'-'+kind,w['id'],kind))
 return w

def audit(d,actor,action,ref):d.execute('INSERT INTO fin_audit(actor,action,reference,created) VALUES(?,?,?,?)',(actor,action,ref,int(time.time())))
def wallet(d,uid):
 w=d.execute('SELECT * FROM fin_wallets WHERE owner=?',(uid,)).fetchone()
 if not w:raise ValueError('Wallet not available')
 return dict(w)
def account(d,uid,kind='available'):return wallet(d,uid)['id']+'-'+kind
def balance(d,aid):
 return d.execute('SELECT COALESCE(SUM(p.amount),0)*a.normal FROM fin_accounts a LEFT JOIN fin_postings p ON p.account=a.id AND EXISTS(SELECT 1 FROM fin_journals j WHERE j.id=p.journal AND j.posted=1) WHERE a.id=? GROUP BY a.id',(aid,)).fetchone()[0]
def amount(v):
 if type(v)!=int or not 1<=v<=MAX_AMOUNT:raise ValueError('Use integer kobo: 1 to 1,000,000 per test transfer')
 return v

def post_journal(d,kind,actor,reference,description,postings):
 if not d.in_transaction:raise RuntimeError('A caller-owned transaction is required')
 if len(postings)<2 or any(type(v)!=int or not v or abs(v)>MAX_BALANCE for v in postings.values()) or sum(postings.values())!=0:raise ValueError('Unbalanced journal')
 for aid,delta in postings.items():
  a=d.execute('SELECT * FROM fin_accounts WHERE id=?',(aid,)).fetchone()
  if not a:raise ValueError('Invalid ledger account')
  after=balance(d,aid)+delta*a['normal']
  if a['wallet'] and not 0<=after<=MAX_BALANCE:raise ValueError('Insufficient available test funds or balance limit exceeded')
 jid=uuid.uuid4().hex
 d.execute('INSERT INTO fin_journals VALUES(?,?,?,?,?,0,?)',(jid,kind,actor,reference,int(time.time()),description))
 for aid,v in postings.items():d.execute('INSERT INTO fin_postings VALUES(?,?,?)',(jid,aid,v))
 d.execute('UPDATE fin_journals SET posted=1 WHERE id=?',(jid,));audit(d,actor,kind,reference)
 for uid in {r[0] for aid in postings for r in d.execute('SELECT w.owner FROM fin_accounts a JOIN fin_wallets w ON w.id=a.wallet WHERE a.id=?',(aid,))}:d.execute('INSERT INTO fin_outbox(owner,journal,created) VALUES(?,?,?)',(uid,jid,int(time.time())))
 return jid

def provision_test_funds(server,uid,value,reference):
 """Explicit disposable-test fixture only. Never exposed as a route or admin button."""
 if not getattr(server,'wallet_fixtures',False):raise PermissionError('Test fixture provisioning is disabled')
 value=amount(value)
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE');existing=d.execute('SELECT id FROM fin_journals WHERE reference=?',(reference,)).fetchone()
  if existing:
   posting=d.execute('SELECT amount FROM fin_postings WHERE journal=? AND account=?',(existing[0],account(d,uid))).fetchone()
   if not posting or posting[0]!=-value:raise ValueError('Conflicting test fixture reference')
   return existing[0]
  return post_journal(d,'test_fixture','fixture',reference,'TEST funds: not real money',{'test-treasury':value,account(d,uid):-value})

def reserve(d,uid,value,reference,expires):
 value=amount(value)
 if type(expires)!=int or not int(time.time())<expires<=time.time()+86400:raise ValueError('Choose a test hold expiry within one day')
 old=d.execute('SELECT * FROM fin_holds WHERE reference=?',(reference,)).fetchone()
 if old:
  if (old['owner'],old['amount'],old['expires'])!=(uid,value,expires):raise ValueError('Conflicting hold reference')
  return old['id']
 if wallet(d,uid)['status']!='active_test':raise PermissionError('Wallet is restricted')
 hid=uuid.uuid4().hex
 post_journal(d,'reserve',uid,'reserve:'+reference,'TEST funds reserved',{account(d,uid):value,account(d,uid,'reserved'):-value})
 d.execute("INSERT INTO fin_holds VALUES(?,?,?,?,?,'reserved',?)",(hid,uid,value,reference,expires,int(time.time())));return hid

def release(d,hid,uid=None):
 h=d.execute('SELECT * FROM fin_holds WHERE id=?',(hid,)).fetchone()
 if not h or uid is not None and uid!=h['owner']:raise PermissionError('Hold not available')
 if h['state']=='released':return
 post_journal(d,'release',h['owner'],'release:'+h['reference'],'TEST reservation released',{account(d,h['owner'],'reserved'):h['amount'],account(d,h['owner']):-h['amount']})
 d.execute("UPDATE fin_holds SET state='released' WHERE id=?",(hid,))

def expire(d,now=None):
 for h in d.execute("SELECT id FROM fin_holds WHERE state='reserved' AND expires<=?",(int(time.time()) if now is None else now,)).fetchall():release(d,h['id'])
def maintenance(server):
 with server.db() as d:d.execute('BEGIN IMMEDIATE');expire(d)

def throttle(server,uid,action,limit):
 # Separate committed transaction: a rejected password must still count toward the limit.
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE');bucket=int(time.time())//60
  n=d.execute('SELECT count FROM fin_rate WHERE owner=? AND action=? AND bucket=?',(uid,action,bucket)).fetchone()
  if n and n[0]>=limit:raise PermissionError('Too many wallet requests; wait a minute')
  d.execute('INSERT INTO fin_rate VALUES(?,?,?,1) ON CONFLICT(owner,action,bucket) DO UPDATE SET count=count+1',(uid,action,bucket))
  d.execute('DELETE FROM fin_rate WHERE bucket<?',(bucket-2,))
def verify_password(server,uid,password):
 throttle(server,uid,'authorize',8)
 if type(password)!=str or not 1<=len(password)<=128:raise PermissionError('Confirm your account password')
 with server.db() as d:stored=d.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0]
 if not stored:raise PermissionError('Set an account password in Settings before test transfers')
 salt=stored.split(':')[0];computed=salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000).hex()
 if not hmac.compare_digest(stored,computed):raise PermissionError('Account password is incorrect')

def overview(d,uid):
 if not d.execute("SELECT 1 FROM fin_permissions p JOIN game_admin a ON a.uid=p.owner WHERE p.owner=? AND p.capability='overview'",(uid,)).fetchone():raise PermissionError('Financial reporting permission required')
 journals=d.execute('SELECT COUNT(*) FROM fin_journals WHERE posted=1').fetchone()[0]
 totals={k:0 for k in ('available','reserved')}
 for a in d.execute("SELECT id,kind FROM fin_accounts WHERE wallet IS NOT NULL"):
  totals[a['kind']]+=balance(d,a['id'])
 unbalanced=d.execute('SELECT COUNT(*) FROM (SELECT j.id FROM fin_journals j LEFT JOIN fin_postings p ON p.journal=j.id WHERE j.posted=1 GROUP BY j.id HAVING COUNT(p.account)<2 OR COALESCE(SUM(p.amount),1)!=0)').fetchone()[0]
 drafts=d.execute('SELECT COUNT(*) FROM fin_journals WHERE posted=0').fetchone()[0]
 treasury=balance(d,'test-treasury')
 transfer_volume=d.execute("SELECT COALESCE(SUM(-p.amount),0) FROM fin_postings p JOIN fin_journals j ON j.id=p.journal WHERE j.kind='transfer' AND j.posted=1 AND p.amount<0").fetchone()[0]
 return {'mode':'test','currency':CURRENCY,'wallets':d.execute('SELECT COUNT(*) FROM fin_wallets').fetchone()[0],'posted_journals':journals,'transfer_volume_kobo':transfer_volume,'available_kobo':totals['available'],'reserved_kobo':totals['reserved'],'test_treasury_kobo':treasury,'reconciliation':{'balanced':not unbalanced and not drafts and treasury==sum(totals.values()),'unbalanced_journals':unbalanced,'draft_journals':drafts,'liability_difference_kobo':treasury-sum(totals.values())},'provider':'Not connected','real_payments_enabled':False}

def get(server,uid,action,q):
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE');expire(d);w=wallet(d,uid)
  if action=='summary':
   finance=bool(d.execute("SELECT 1 FROM fin_permissions p JOIN game_admin a ON a.uid=p.owner WHERE p.owner=? AND p.capability='overview'",(uid,)).fetchone())
   return dict(w,mode='test',real_payments_enabled=False,available_kobo=balance(d,account(d,uid)),reserved_kobo=balance(d,account(d,uid,'reserved')),finance_overview=finance,transfer_limit_kobo=MAX_AMOUNT,daily_limit_kobo=DAILY_LIMIT,provider='Not connected')
  if action=='history':
   try:before=int(q.get('before',['9223372036854775807'])[0])
   except (ValueError,TypeError):raise ValueError('Invalid history cursor')
   records=[dict(r) for r in d.execute('SELECT j.rowid cursor,j.id,j.kind,j.reference,j.created,j.description,COALESCE(SUM(CASE WHEN a.kind=\'available\' THEN -p.amount ELSE 0 END),0) available_change_kobo,COALESCE(SUM(CASE WHEN a.kind=\'reserved\' THEN -p.amount ELSE 0 END),0) reserved_change_kobo FROM fin_journals j JOIN fin_postings p ON p.journal=j.id JOIN fin_accounts a ON a.id=p.account WHERE a.wallet=? AND j.posted=1 AND j.rowid<? GROUP BY j.id ORDER BY j.rowid DESC LIMIT 30',(w['id'],before))]
   for record in records:
    record['counterparties']=[dict(r) for r in d.execute('SELECT DISTINCT u.id,u.name,u.nickname FROM fin_postings p JOIN fin_accounts a ON a.id=p.account JOIN fin_wallets w ON w.id=a.wallet JOIN users u ON u.id=w.owner WHERE p.journal=? AND w.owner!=?',(record['id'],uid))]
   return {'mode':'test','currency':CURRENCY,'transactions':records,'next_before':records[-1]['cursor'] if len(records)==30 else None}
  if action=='notices':return {'mode':'test','notices':[dict(r) for r in d.execute('SELECT id,journal,created FROM fin_outbox WHERE owner=? ORDER BY id DESC LIMIT 30',(uid,))]}
  if action=='overview':return overview(d,uid)
  raise ValueError('Wallet operation is not supported in Phase B')

def post(server,uid,action,b):
 if action not in ('quote','transfer'):raise PermissionError('Real funding, withdrawals and tournament payments are disabled')
 if action=='quote':
  throttle(server,uid,'quote',20);value=amount(b.get('amount_kobo'));identity=b.get('recipient')
  if type(identity)!=str or not 1<=len(identity)<=40:raise ValueError('Choose an X ORBIT recipient')
  with server.db() as d:
   d.execute('BEGIN IMMEDIATE');w=wallet(d,uid)
   if w['status']!='active_test':raise PermissionError('Wallet is restricted')
   # Immutable IDs win over nickname ambiguity; confirmation fixes the resolved ID.
   other=d.execute('SELECT id,name,nickname FROM users WHERE id=?',(identity,)).fetchone() or d.execute('SELECT id,name,nickname FROM users WHERE nickname=? COLLATE NOCASE',(identity.lstrip('@'),)).fetchone()
   if not other or other['id']==uid:raise ValueError('Choose another existing account')
   if wallet(d,other['id'])['status']!='active_test':raise ValueError('Recipient wallet is restricted')
   qid=secrets.token_urlsafe(24);expiry=int(time.time())+120
   d.execute('INSERT INTO fin_quotes VALUES(?,?,?,?,?,0)',(qid,uid,other['id'],value,expiry));d.execute('DELETE FROM fin_quotes WHERE expires<?',(int(time.time())-86400,))
   return {'mode':'test','quote':qid,'recipient':dict(other),'amount_kobo':value,'fee_kobo':0,'currency':CURRENCY,'expires':expiry}
 key=b.get('idempotency_key');qid=b.get('quote')
 if type(key)!=str or not re.fullmatch(r'[a-zA-Z0-9_-]{16,80}',key) or type(qid)!=str or not 1<=len(qid)<=80:raise ValueError('Valid confirmation and idempotency key required')
 verify_password(server,uid,b.get('password'));fingerprint=hashlib.sha256(qid.encode()).hexdigest()
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE');expire(d)
  previous=d.execute('SELECT * FROM fin_operations WHERE actor=? AND key=?',(uid,key)).fetchone()
  if previous:
   if previous['fingerprint']!=fingerprint:raise ValueError('Idempotency key belongs to another request')
   return json.loads(previous['result'])
  quote=d.execute('SELECT * FROM fin_quotes WHERE id=? AND actor=?',(qid,uid)).fetchone()
  if not quote or quote['used'] or quote['expires']<=time.time():raise ValueError('Confirmation expired or already used; prepare a new transfer')
  for u in (uid,quote['recipient']):
   if wallet(d,u)['status']!='active_test':raise PermissionError('A wallet is restricted')
  used=d.execute("SELECT COALESCE(SUM(p.amount),0) FROM fin_postings p JOIN fin_journals j ON j.id=p.journal WHERE j.actor=? AND j.kind='transfer' AND j.posted=1 AND p.account=? AND j.created>?",(uid,account(d,uid),int(time.time())-86400)).fetchone()[0]
  if used+quote['amount']>DAILY_LIMIT:raise ValueError('Rolling 24-hour test transfer limit reached')
  jid=post_journal(d,'transfer',uid,'transfer:'+uid+':'+key,'TEST transfer: not real money',{account(d,uid):quote['amount'],account(d,quote['recipient']):-quote['amount']})
  result={'mode':'test','transaction':jid,'reference':'transfer:'+uid+':'+key,'amount_kobo':quote['amount'],'currency':CURRENCY,'recipient':quote['recipient'],'status':'posted'}
  d.execute('UPDATE fin_quotes SET used=1 WHERE id=?',(qid,));d.execute('INSERT INTO fin_operations VALUES(?,?,?,?)',(uid,key,fingerprint,json.dumps(result)));return result
