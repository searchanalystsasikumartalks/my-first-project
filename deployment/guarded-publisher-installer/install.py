"""Create-only installation of pinned publisher files. No cron, auto grant or public writes."""
import argparse,ctypes,fcntl,hashlib,json,os,stat,sys,uuid
from pathlib import Path
HOME='/home/dzfbipjkvhxg';LOCAL=HOME+'/.local';TARGET='appstudio-deployer';WORK='.appstudio-install-v2';APPS=HOME+'/public_html/appln/apps'
SOURCE=str(Path(__file__).resolve().parent/'payload')
PINS={'entry.py': '4b10f9ec1b14c74b89915cf9d7fae8e19a94a6406fd85bda6dbc97e9c97ae569', 'studio.py': 'aff5a80d5fc020febdb3b5718e2a635925488e85724eee203dfc46fa3263a231', 'primitives.py': 'fb14c4cd5241da2d6b13fb2494fa8bf3877e2efbbf3f4190f525141281a45087', 'git_source.py': 'f5a3f39cf0fe2ebb12b7bc4eae3a749b86a59c8fd9420f8d969765ecfcb1a8db', 'coordinator_entry.py': '7879ac3ec2bddff227d7e180facc053fd767085e874137ab77b27c44c93a7de6', 'coordinator.py': 'ece0ac4c9be6d6024dd81e4aa5fb8629003545a678de428302c9e68b7adaef06', 'intake.py': '1f4850445000799e05df82a3ab26d7c5fb8d5874713958f875d4acbd91896224', 'repo_refresh.py': '9cb94e8eb74a4653d2d5bdba4187524be62e048ac54e7ea146565eb45e8b9eda'}
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
class Refused(RuntimeError):pass

def directory(path):
 fd=os.open('/',DIR)
 try:
  for part in path.split('/')[1:]:
   if part in ('','.','..'):raise Refused('invalid path')
   n=os.open(part,DIR,dir_fd=fd);os.close(fd);fd=n
  return fd
 except BaseException:os.close(fd);raise

def identity(fd):s=os.fstat(fd);return [s.st_dev,s.st_ino]
def read(fd,name):
 f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
 try:
  st=os.fstat(f)
  if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size>1048576:raise Refused('unsafe file')
  data=b''
  while len(data)<=1048576:
   x=os.read(f,min(65536,1048577-len(data)))
   if not x:break
   data+=x
  end=os.fstat(f);cur=os.stat(name,dir_fd=fd,follow_symlinks=False)
  key=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns,x.st_nlink)
  if len(data)>1048576 or key(st)!=key(end) or key(end)!=key(cur):raise Refused('file changed')
  return data,st
 finally:os.close(f)
def write(fd,name,data):
 f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
 try:
  while data:data=data[os.write(f,data):]
  os.fsync(f)
 finally:os.close(f)
def encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def initialized():return {'registry.json':encoded({'version':1,'revision':0,'apps':{}}),'automatic-state.json':encoded({'version':1,'last_tip':None,'draft':None,'attempts':{}}),'automatic-policy.json':encoded({'version':1,'mode':'draft','authority_id':'installation-draft-only','scopes':[]})}
def snapshot(fd):
 names=set(PINS)|set(initialized())
 if set(os.listdir(fd))!=names:raise Refused('unexpected installation file set')
 s=os.fstat(fd)
 if stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.geteuid():raise Refused('unsafe payload directory')
 out={}
 for n in sorted(names):
  data,st=read(fd,n)
  if stat.S_IMODE(st.st_mode)!=0o600 or st.st_uid!=os.geteuid():raise Refused('unsafe payload permissions')
  out[n]=hashlib.sha256(data).hexdigest()
 return {'identity':identity(fd),'hashes':out}
def expected():return dict(PINS,**{k:hashlib.sha256(v).hexdigest() for k,v in initialized().items()})
def rename(src,srcname,dst,dstname):
 lib=ctypes.CDLL(None,use_errno=True);fn=getattr(lib,'renameat2',None)
 if fn is None:raise Refused('renameat2 unavailable')
 fn.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint);fn.restype=ctypes.c_int
 if fn(src,srcname.encode(),dst,dstname.encode(),1):raise OSError(ctypes.get_errno(),'no-replace installation refused')
class Installer:
 def __init__(self):
  self.fds=[]
  try:
   self.home=directory(HOME);self.fds.append(self.home);self.local=directory(LOCAL);self.fds.append(self.local);self.apps=directory(APPS);self.fds.append(self.apps)
   for f in (self.home,self.local):
    s=os.fstat(f)
    if s.st_uid!=os.geteuid() or s.st_mode&0o022:raise Refused('existing parent ownership/mode unsafe; not changed')
   if len({os.fstat(f).st_dev for f in self.fds})!=1:raise Refused('same filesystem required')
   self.parents=[identity(self.home),identity(self.local)]
   l=os.open('.appstudio-install-v2.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.home);self.fds.append(l);s=os.fstat(l)
   if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600 or s.st_uid!=os.geteuid():raise Refused('unsafe install lock')
   fcntl.flock(l,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BaseException:self.close();raise
 def close(self):
  for f in reversed(self.fds):os.close(f)
  self.fds=[]
 def check_parent(self):
  for path,old in zip((HOME,LOCAL),self.parents):
   f=directory(path)
   try:
    if identity(f)!=old:raise Refused('parent replaced')
   finally:os.close(f)
 def existing(self,parent,name):
  try:os.stat(name,dir_fd=parent,follow_symlinks=False);return True
  except FileNotFoundError:return False
 def prepare(self):
  self.check_parent()
  if self.existing(self.local,TARGET) or self.existing(self.home,WORK):raise Refused('target or installation attempt exists; reconcile, never overwrite')
  source=directory(SOURCE)
  try:
   data={n:read(source,n)[0] for n in PINS}
   if any(hashlib.sha256(data[n]).hexdigest()!=PINS[n] for n in PINS):raise Refused('pinned source mismatch')
  finally:os.close(source)
  os.mkdir(WORK,0o700,dir_fd=self.home);os.fsync(self.home);w=os.open(WORK,DIR,dir_fd=self.home)
  try:
   os.mkdir('payload',0o700,dir_fd=w);p=os.open('payload',DIR,dir_fd=w)
   try:
    for n,b in dict(data,**initialized()).items():write(p,n,b)
    os.fsync(p);snap=snapshot(p)
   finally:os.close(p)
   j={'version':1,'phase':'prepared','parents':self.parents,'payload':snap}
   write(w,'journal.json',encoded(j));os.fsync(w);return j
  finally:os.close(w)
 def journal(self):
  w=os.open(WORK,DIR,dir_fd=self.home)
  try:
   b,_=read(w,'journal.json');j=json.loads(b)
   if set(j)!={'version','phase','parents','payload'} or type(j['version'])is not int or j['version']!=1 or j['phase'] not in ('prepared','installing','installed') or j['parents']!=self.parents or set(j['payload'])!={'identity','hashes'} or j['payload']['hashes']!=expected():raise Refused('invalid bound installation journal')
   return w,j
  except BaseException:os.close(w);raise
 def phase(self,w,j,value):
  j['phase']=value;t='journal-'+uuid.uuid4().hex+'.tmp';write(w,t,encoded(j));os.rename(t,'journal.json',src_dir_fd=w,dst_dir_fd=w);os.fsync(w)
 def classify(self,w,j):
  self.check_parent();a=self.existing(w,'payload');b=self.existing(self.local,TARGET)
  if a==b:raise Refused('unexpected installation state')
  f=os.open('payload' if a else TARGET,DIR,dir_fd=w if a else self.local)
  try:
   if snapshot(f)!=j['payload']:raise Refused('installation changed; no overwrite')
  finally:os.close(f)
  return 'prepared' if a else 'installed'
 def reconcile(self):
  w,j=self.journal()
  try:return {'phase':j['phase'],'observed':self.classify(w,j),'target':LOCAL+'/'+TARGET}
  finally:os.close(w)
 def apply(self,hook=lambda _:None):
  w,j=self.journal()
  try:
   actual=self.classify(w,j)
   if actual=='installed':
    os.fsync(w);os.fsync(self.local);self.phase(w,j,'installed');return {'status':'already_installed_verified','target':LOCAL+'/'+TARGET}
   if j['phase']!='prepared':raise Refused('uncertain prepared attempt requires review; not replayed')
   self.phase(w,j,'installing');hook('before_rename');self.check_parent()
   if self.classify(w,j)!='prepared':raise Refused('state changed')
   rename(w,'payload',self.local,TARGET);hook('after_rename');os.fsync(w);os.fsync(self.local)
   if self.classify(w,j)!='installed':raise Refused('unexpected installation result')
   self.phase(w,j,'installed');return {'status':'installed_draft_only','target':LOCAL+'/'+TARGET}
  finally:os.close(w)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','apply','reconcile']);a=p.parse_args();i=None
 try:
  if sys.version_info<(3,10):raise Refused('Python3.10+ required')
  i=Installer();r=getattr(i,a.action)();print(json.dumps({'ok':True,'result':r}));return 0
 except Exception as e:print(json.dumps({'ok':False,'error':str(e),'next':'Reconcile existing attempt; never delete/reset state to retry.'}));return 1
 finally:
  if i:i.close()
if __name__=='__main__':raise SystemExit(main())
