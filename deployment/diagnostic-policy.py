"""Exact one-app local policy transition. No cron, app publication or code changes."""
import argparse,hashlib,json,os,stat,sys,uuid
PRIVATE='/home/dzfbipjkvhxg/.local/appstudio-deployer'
APP_ID='f926d758-47b8-4328-a2a6-e4d29a837e07';SLUG='deployment-check-20261109'
BEFORE={'version':1,'mode':'draft','authority_id':'installation-draft-only','scopes':[]}
AFTER={'version':1,'mode':'auto','authority_id':'owner-supervised-diagnostic-20261109','scopes':[{'app_id':APP_ID,'slug':SLUG,'operations':['create','update']}]}
def data(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
BEFORE_HASH=hashlib.sha256(data(BEFORE)).hexdigest();AFTER_HASH=hashlib.sha256(data(AFTER)).hexdigest()
class Refused(RuntimeError):pass
def read(fd):
 f=os.open('automatic-policy.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
 try:
  s=os.fstat(f)
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600 or s.st_uid!=os.geteuid() or s.st_size>65536:raise Refused('unsafe policy metadata')
  b=os.read(f,65537);t=os.fstat(f);u=os.stat('automatic-policy.json',dir_fd=fd,follow_symlinks=False)
  key=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns,x.st_uid,x.st_gid,stat.S_IMODE(x.st_mode))
  if key(s)!=key(t) or key(t)!=key(u) or len(b)!=s.st_size:raise Refused('policy changed during read')
  return b,key(s)
 finally:os.close(f)
def transition(studio,action,hook=lambda:None):
 if action not in ('enable','restore-draft'):raise Refused('unsupported action')
 expected=data(BEFORE if action=='enable' else AFTER)
 desired=data(AFTER if action=='enable' else BEFORE)
 old,identity=read(studio.root)
 if old!=expected:raise Refused('exact expected policy revision mismatch; no overwrite')
 name='policy-transition-'+uuid.uuid4().hex+'.tmp';f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=studio.root)
 try:
  if os.fstat(f).st_gid!=identity[6]:os.fchown(f,-1,identity[6])
  b=desired
  while b:b=b[os.write(f,b):]
  os.fsync(f)
 finally:os.close(f)
 # The caller owns the installed Studio lock. Same-user uncooperative mutation remains unsupported.
 hook();now,current=read(studio.root)
 if now!=old or current!=identity:raise Refused('policy changed before replace; temporary file retained')
 os.rename(name,'automatic-policy.json',src_dir_fd=studio.root,dst_dir_fd=studio.root);os.fsync(studio.root)
 actual,_=read(studio.root)
 if actual!=desired:raise Refused('uncertain result; inspect current policy, never replay')
 return {'action':action,'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(actual).hexdigest(),'app_id':APP_ID,'slug':SLUG,'cron_changed':False,'published':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','enable','restore-draft']);a=p.parse_args();s=None
 try:
  sys.path.insert(0,PRIVATE);import studio
  s=studio.Studio()
  if a.action=='inspect':
   b,_=read(s.root);r={'sha256':hashlib.sha256(b).hexdigest(),'matches_pristine_draft':b==data(BEFORE),'matches_exact_diagnostic_auto':b==data(AFTER)}
  else:r=transition(s,a.action)
  print(json.dumps({'ok':True,'result':r}));return 0
 except Exception as e:print(json.dumps({'ok':False,'error':str(e),'next':'Inspect policy before retry; do not replace unrelated or changed state.'}));return 1
 finally:
  if s:s.close()
if __name__=='__main__':raise SystemExit(main())
