#!/usr/bin/env python3
"""Self-hosted FOT training. No AI model, chatbot, keys or external API needed."""
import hashlib,hmac,ipaddress,json,os,sqlite3,threading,time
from datetime import datetime,timezone
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'public'
CASES=json.loads((ROOT/'cases.json').read_text())
DATA=Path(os.environ.get('FOT_DATA_DIR','/var/lib/fot-manager-training'))
DB=DATA/'completions.sqlite3'
ORIGINS=set(os.environ.get('FOT_ALLOWED_ORIGINS','https://fot-manager-training.ru,https://www.fot-manager-training.ru,http://fot-manager-training.ru,http://www.fot-manager-training.ru').split(','))
TRUST_PROXY=os.environ.get('FOT_TRUST_PROXY','0')=='1'
KEY=None
LIMITS={};LOCK=threading.Lock()

@contextmanager
def connection():
 db=sqlite3.connect(DB,timeout=15);db.execute('PRAGMA busy_timeout=15000')
 try:
  yield db
  db.commit()
 except Exception:
  db.rollback();raise
 finally:db.close()

def initialize():
 global KEY
 DATA.mkdir(parents=True,exist_ok=True)
 keyfile=DATA/'visitor-hash.key'
 if not keyfile.exists():
  with keyfile.open('xb') as stream:os.chmod(keyfile,0o600);stream.write(os.urandom(48))
 KEY=keyfile.read_bytes()
 if len(KEY)<32:raise RuntimeError('Invalid statistics key file')
 with connection() as db:
  db.execute('PRAGMA journal_mode=WAL')
  db.execute("CREATE TABLE IF NOT EXISTS training_completions (segment TEXT NOT NULL CHECK(segment IN ('kksb','rgs','mmb')), visitor_hash TEXT NOT NULL CHECK(length(visitor_hash)=64), completed_at TEXT NOT NULL, PRIMARY KEY(segment,visitor_hash))")

def normalize_ip(value):
 try:
  value=ipaddress.ip_address(value)
  return str(value.ipv4_mapped if isinstance(value,ipaddress.IPv6Address) and value.ipv4_mapped else value)
 except ValueError:return None

def valid_completion(body):
 if not isinstance(body,dict) or not isinstance(body.get('segment'),str):return False
 case=CASES.get(body.get('segment'));a=body.get('attempt')
 if not case or not isinstance(a,dict) or a.get('version')!=case['version'] or a.get('status')!='done' or a.get('index')!=len(case['questions'])-1 or not isinstance(a.get('answers'),dict):return False
 for q in case['questions']:
  entry=a['answers'].get(q['id']);selected=entry.get('selected') if isinstance(entry,dict) else None;feedback=entry.get('feedback') if isinstance(entry,dict) else None
  if not isinstance(selected,list) or not selected or any(type(i) is not int or i<0 or i>=q['options'] for i in selected) or len(set(selected))!=len(selected) or not isinstance(feedback,dict) or type(feedback.get('correct')) is not bool:return False
  if q['required'] and sorted(selected)!=q['correct']:return False
 quiz=a.get('quiz') or {};answers=quiz.get('answers') if isinstance(quiz,dict) else None
 for i,correct in enumerate(case['quiz']):
  entry=answers[i] if isinstance(answers,list) and i<len(answers) else answers.get(str(i),answers.get(i)) if isinstance(answers,dict) else None
  if not isinstance(entry,dict) or entry.get('correct') is not True or not isinstance(entry.get('selected'),list) or any(type(n) is not int for n in entry['selected']) or sorted(entry['selected'])!=correct:return False
 return True

class Handler(SimpleHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(PUBLIC),**kwargs)
 def log_message(self,fmt,*args):print(datetime.now(timezone.utc).isoformat(),fmt%args,flush=True)
 def list_directory(self,path):self.send_error(404);return None
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
 def result(self,data,status=200):
  payload=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store')
  origin=self.headers.get('Origin')
  if origin in ORIGINS:self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
  self.end_headers()
  if self.command!='HEAD':self.wfile.write(payload)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/health':
   try:
    with connection() as db:db.execute('SELECT 1').fetchone()
    return self.result({'ready':True,'mode':'training-without-ai'})
   except sqlite3.Error:return self.result({'ready':False},503)
  if path=='/api/training/completions':
   try:
    with connection() as db:rows=db.execute('SELECT segment,COUNT(*) FROM training_completions GROUP BY segment').fetchall()
    counts={'kksb':0,'rgs':0,'mmb':0};counts.update(dict(rows));return self.result({'counts':counts})
   except sqlite3.Error:return self.result({'message':'Счётчик временно недоступен.'},503)
  if path.startswith('/api/'):return self.result({'message':'Раздел не найден.'},404)
  return super().do_GET()
 def do_HEAD(self):
  return self.do_GET() if urlsplit(self.path).path.startswith('/api/') else super().do_HEAD()
 def do_OPTIONS(self):
  if self.headers.get('Origin') not in ORIGINS:return self.result({'message':'Источник запроса не разрешён.'},403)
  self.send_response(204);self.send_header('Content-Length','0');self.send_header('Access-Control-Allow-Origin',self.headers['Origin']);self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Vary','Origin');self.end_headers()
 def do_POST(self):
  self.close_connection=True
  if urlsplit(self.path).path!='/api/training/completions':return self.result({'message':'Раздел не найден.'},404)
  if self.headers.get('Origin') not in ORIGINS:return self.result({'message':'Источник запроса не разрешён.'},403)
  if not self.headers.get('Content-Type','').startswith('application/json'):return self.result({'message':'Ожидается JSON.'},415)
  try:length=int(self.headers.get('Content-Length','0'))
  except ValueError:return self.result({'message':'Некорректный запрос.'},400)
  if not 0<length<=30000:self.close_connection=True;return self.result({'message':'Слишком большой запрос.'},413)
  try:body=json.loads(self.rfile.read(length))
  except (ValueError,UnicodeDecodeError):return self.result({'message':'Некорректный запрос.'},400)
  if not valid_completion(body):return self.result({'message':'Для зачёта необходимо завершить все вопросы бизнес-кейса.'},400)
  peer=normalize_ip(self.client_address[0])
  address=self.headers.get('X-Real-IP',peer) if TRUST_PROXY and peer and ipaddress.ip_address(peer).is_loopback else peer
  address=normalize_ip(address)
  if not address:return self.result({'message':'Не удалось определить участника.'},503)
  segment=body['segment'];visitor=hmac.new(KEY,(segment+'\n'+address).encode(),hashlib.sha256).hexdigest()
  with LOCK:
   start,count=LIMITS.get(visitor,(time.monotonic(),0));now=time.monotonic()
   if now-start>=60:start,count=now,0
   LIMITS[visitor]=(start,count+1)
   if len(LIMITS)>10000:LIMITS.clear()
   if count>=20:return self.result({'message':'Повторите запрос через минуту.'},429)
  try:
   with connection() as db:
    cursor=db.execute('INSERT INTO training_completions(segment,visitor_hash,completed_at) VALUES(?,?,?) ON CONFLICT(segment,visitor_hash) DO NOTHING',(segment,visitor,datetime.now(timezone.utc).isoformat()))
    counted=cursor.rowcount>0;total=db.execute('SELECT COUNT(*) FROM training_completions WHERE segment=?',(segment,)).fetchone()[0]
   return self.result({'segment':segment,'total':total,'counted':counted})
  except sqlite3.Error:return self.result({'message':'Счётчик временно недоступен. Завершение будет отправлено позже.'},503)

if __name__=='__main__':
 initialize()
 server=ThreadingHTTPServer((os.environ.get('FOT_LISTEN_HOST','127.0.0.1'),int(os.environ.get('FOT_PORT','8766'))),Handler)
 print('FOT training backend listening on loopback; no AI services configured.',flush=True)
 server.serve_forever()
