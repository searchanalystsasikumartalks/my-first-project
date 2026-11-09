"""Fixed-root, approval-bound static multi-app publisher. No autonomous deployment."""
import argparse,fcntl,hashlib,json,os,re,stat,sys,uuid,unicodedata
from primitives import Refused,FILES,FLAGS,manifest,identity,open_dir,rename
import git_source
HOME='/home/dzfbipjkvhxg'
APPS=HOME+'/public_html/appln/apps'
PRIVATE=HOME+'/.local/appstudio-deployer'
RESERVED={'a','admin','master','assets','api','static','index','deployment','catalog-preview'}

def appid(value):
    if not isinstance(value,str):raise Refused('invalid app id')
    try:ok=str(uuid.UUID(value))==value and uuid.UUID(value).int!=0
    except ValueError:ok=False
    if not ok:raise Refused('canonical UUID app id required')
    return value

def slug(value):
    if not isinstance(value,str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',value) or len(value)>63 or value in RESERVED:raise Refused('invalid or reserved slug')
    return value

def display(value):
    if not isinstance(value,str) or value!=value.strip() or not 1<=len(value)<=80 or any(ord(c)<32 or 127<=ord(c)<=159 or 0xD800<=ord(c)<=0xDFFF for c in value):raise Refused('invalid display name')
    return value

def display_key(value):return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())

def hashes(value):
    if not isinstance(value,dict) or set(value)!=set(FILES) or any(not isinstance(h,str) or not re.fullmatch('[a-f0-9]{64}',h) for h in value.values()):raise Refused('exact four static file hashes required')
    return value

def revision(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise Refused('duplicate JSON key')
        result[k]=v
    return result

def canonical(path):
    if not path.startswith('/') or any(v in ('','.','..') for v in path.split('/')[1:]):raise Refused('invalid absolute directory')
    fd=os.open('/',FLAGS)
    try:
        for p in path.split('/')[1:]:n=os.open(p,FLAGS,dir_fd=fd);os.close(fd);fd=n
        return fd
    except BaseException:os.close(fd);raise

def read_json(fd,name,limit=1048576):
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        a=os.fstat(f)
        if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or not 0<a.st_size<=limit:raise Refused('unsafe JSON file')
        data=b''
        while len(data)<=limit:
            part=os.read(f,min(65536,limit+1-len(data)))
            if not part:break
            data+=part
        if len(data)>limit:raise Refused('JSON too large')
        b=os.fstat(f);c=os.stat(name,dir_fd=fd,follow_symlinks=False)
        k=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if k(a)!=k(b) or k(b)!=k(c):raise Refused('JSON changed while reading')
        return json.loads(data,object_pairs_hook=unique)
    finally:os.close(f)

def write_json(fd,name,value,initial=False):
    data=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    if len(data)>1048576:raise Refused('JSON too large')
    if initial:
        reserve=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd);os.close(reserve);os.fsync(fd)
    temp=name+'.tmp-'+uuid.uuid4().hex;f=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        while data:data=data[os.write(f,data):]
        os.fsync(f)
    finally:os.close(f)
    os.rename(temp,name,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)

def valid_entry(e):
    if not isinstance(e,dict) or set(e)!={'app_id','slug','display_name','commit','hashes','revision','identity'}:raise Refused('invalid registry entry')
    appid(e['app_id']);slug(e['slug']);display(e['display_name']);hashes(e['hashes'])
    if not isinstance(e['commit'],str) or not re.fullmatch('[a-f0-9]{40}',e['commit']) or e['revision']!=revision(e['hashes']):raise Refused('invalid registry revision')
    if not isinstance(e['identity'],list) or len(e['identity'])!=2 or any(type(v)is not int or v<0 for v in e['identity']) or e['identity'][1]==0:raise Refused('invalid registry inode')

def proposal(p):
    if not isinstance(p,dict) or set(p)!={'app_id','slug','display_name','operation','commit','hashes','expected_revision'}:raise Refused('invalid proposal schema')
    appid(p['app_id']);slug(p['slug']);display(p['display_name']);hashes(p['hashes'])
    if p['operation'] not in ('create','update') or not isinstance(p['commit'],str) or not re.fullmatch('[a-f0-9]{40}',p['commit']):raise Refused('invalid operation or commit')
    if p['operation']=='create' and p['expected_revision'] is not None:raise Refused('create cannot have old revision')
    if p['operation']=='update' and (not isinstance(p['expected_revision'],str) or not re.fullmatch('[a-f0-9]{64}',p['expected_revision'])):raise Refused('update requires old revision')
    return p

class Studio:
    def __init__(self):
        self.fds=[]
        try:
            self.apps=canonical(APPS);self.fds.append(self.apps);self.root=canonical(PRIVATE);self.fds.append(self.root)
            if os.fstat(self.root).st_mode&0o077:raise Refused('private control directory must be owner-only')
            self.parent_id=identity(self.apps)
            lock=os.open('lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.root);self.fds.append(lock)
            s=os.fstat(lock)
            if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise Refused('unsafe control lock')
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self.close();raise
    def close(self):
        for fd in reversed(self.fds):os.close(fd)
        self.fds=[]
    def check_parent(self):
        f=canonical(APPS)
        try:
            if identity(f)!=self.parent_id:raise Refused('apps parent changed')
        finally:os.close(f)
    def init_registry(self):write_json(self.root,'registry.json',{'version':1,'revision':0,'apps':{}},initial=True)
    def registry(self):
        r=read_json(self.root,'registry.json')
        if not isinstance(r,dict) or set(r)!={'version','revision','apps'} or type(r['version'])is not int or r['version']!=1 or type(r['revision'])is not int or r['revision']<0 or not isinstance(r['apps'],dict):raise Refused('invalid registry')
        names=set();slugs=set()
        for key,e in r['apps'].items():
            valid_entry(e)
            if key!=e['app_id'] or e['slug'] in slugs or display_key(e['display_name']) in names:raise Refused('registry collision')
            slugs.add(e['slug']);names.add(display_key(e['display_name']))
        return r
    def state(self,fd,name,absent=False):
        try:f=open_dir(fd,name)
        except FileNotFoundError:
            if absent:return None
            raise
        try:return {'identity':identity(f),'hashes':manifest(f)}
        finally:os.close(f)
    def collision(self,r,p):
        for aid,e in r['apps'].items():
            if aid!=p['app_id'] and (e['slug']==p['slug'] or display_key(e['display_name'])==display_key(p['display_name'])):raise Refused('app name or slug already registered')
        for name in os.listdir(self.apps):
            if name.casefold()==p['slug'].casefold() and name!=p['slug']:raise Refused('filesystem case collision')
    def prepare(self,transaction,p,approval_digest):
        transaction=appid(transaction);p=proposal(p)
        # Explicit approval digest binds exactly this JSON proposal. Invocation still requires owner authorization.
        if approval_digest!=revision(p):raise Refused('exact proposal approval digest required')
        self.check_parent();reg=self.registry();self.collision(reg,p);old=reg['apps'].get(p['app_id'])
        before=self.state(self.apps,p['slug'],True)
        if p['operation']=='create':
            if old is not None or before is not None:raise Refused('create target or app id already exists')
        else:
            if old is None or old['slug']!=p['slug'] or old['revision']!=p['expected_revision'] or before!={'identity':old['identity'],'hashes':old['hashes']}:raise Refused('unknown app, changed path, or stale live revision')
        if git_source.git(['remote','get-url','origin'],4096).decode().strip()!=git_source.REMOTE:raise Refused('fixed repository mismatch')
        if git_source.git(['cat-file','-t',p['commit']],128).decode().strip()!='commit':raise Refused('exact commit object required')
        dirname='txn-'+transaction;os.mkdir(dirname,0o700,dir_fd=self.root);d=open_dir(self.root,dirname)
        try:
            os.mkdir('slot',0o700,dir_fd=d);slot=open_dir(d,'slot')
            try:
                if os.fstat(slot).st_dev!=os.fstat(self.apps).st_dev:raise Refused('same filesystem required')
                for name in FILES:
                    data=git_source.git(['show',p['commit']+':static-apps/'+p['app_id']+'/'+name])
                    if b'\0' in data:raise Refused('static UTF-8 content required')
                    data.decode('utf-8')
                    if hashlib.sha256(data).hexdigest()!=p['hashes'][name]:raise Refused('approved content differs')
                    f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=slot)
                    try:
                        view=memoryview(data)
                        while view:view=view[os.write(f,view):]
                        os.fchmod(f,0o644);os.fsync(f)
                    finally:os.close(f)
                os.fchmod(slot,0o755);os.fsync(slot);os.fsync(d)
            finally:os.close(slot)
            after=self.state(d,'slot');new={'app_id':p['app_id'],'slug':p['slug'],'display_name':p['display_name'],'commit':p['commit'],'hashes':p['hashes'],'revision':revision(p['hashes']),'identity':after['identity']}
            r={'version':1,'transaction':transaction,'phase':'prepared','parent':self.parent_id,'proposal':p,'approval_digest':approval_digest,'before':before,'after':after,'old_entry':old,'new_entry':new}
            write_json(d,'journal.json',r,initial=True);os.fsync(self.root);return r
        finally:os.close(d)
    def journal(self,transaction):
        transaction=appid(transaction);d=open_dir(self.root,'txn-'+transaction)
        try:r=read_json(d,'journal.json')
        except BaseException:os.close(d);raise
        try:
            if not isinstance(r,dict) or set(r)!={'version','transaction','phase','parent','proposal','approval_digest','before','after','old_entry','new_entry'} or type(r['version'])is not int or r['version']!=1 or r['transaction']!=transaction or r['parent']!=self.parent_id or r['phase'] not in ('prepared','applying','committed','rolling_back','rolled_back'):raise Refused('journal binding invalid')
            p=proposal(r['proposal']);valid_entry(r['new_entry'])
            if r['old_entry'] is not None:valid_entry(r['old_entry'])
            if r['approval_digest']!=revision(p) or r['new_entry']['app_id']!=p['app_id'] or r['new_entry']['slug']!=p['slug'] or r['new_entry']['hashes']!=p['hashes'] or r['new_entry']['commit']!=p['commit'] or r['new_entry']['display_name']!=p['display_name']:raise Refused('journal proposal mismatch')
            for key in ('before','after'):
                s=r[key]
                if key=='before' and s is None:continue
                if not isinstance(s,dict) or set(s)!={'identity','hashes'}:raise Refused('invalid journal snapshot')
                hashes(s['hashes']);ids=s['identity']
                if not isinstance(ids,list) or len(ids)!=2 or any(type(v)is not int or v<0 for v in ids) or ids[1]==0:raise Refused('invalid journal inode')
            if r['after']!={'identity':r['new_entry']['identity'],'hashes':r['new_entry']['hashes']}:raise Refused('new entry identity mismatch')
            if p['operation']=='create':
                if r['old_entry'] is not None or r['before'] is not None:raise Refused('create journal conflict')
            elif r['old_entry'] is None or r['before']!={'identity':r['old_entry']['identity'],'hashes':r['old_entry']['hashes']} or r['old_entry']['app_id']!=p['app_id'] or r['old_entry']['slug']!=p['slug'] or r['old_entry']['revision']!=p['expected_revision']:raise Refused('update journal conflict')
            return d,r
        except BaseException:os.close(d);raise
    def classify(self,d,r):
        self.check_parent();live=self.state(self.apps,r['proposal']['slug'],True);slot=self.state(d,'slot',True)
        if live==r['before'] and slot==r['after']:fs='original'
        elif live==r['after'] and slot==r['before']:fs='updated'
        else:raise Refused('unexpected live or backup state')
        reg=self.registry();entry=reg['apps'].get(r['proposal']['app_id']);self.collision(reg,r['proposal'])
        if entry==r['old_entry']:rs='original'
        elif entry==r['new_entry']:rs='updated'
        else:raise Refused('registry entry changed')
        return {'files':fs,'registry':rs}
    def reconcile(self,transaction):
        d,r=self.journal(transaction)
        try:return self.classify(d,r)
        finally:os.close(d)
    def registry_set(self,r,new):
        reg=self.registry();aid=r['proposal']['app_id'];current=reg['apps'].get(aid)
        expected=r['old_entry'] if new else r['new_entry'];desired=r['new_entry'] if new else r['old_entry']
        if current==desired:return
        if current!=expected:raise Refused('registry changed; refusing overwrite')
        if desired is None:reg['apps'].pop(aid,None)
        else:reg['apps'][aid]=desired
        reg['revision']+=1;write_json(self.root,'registry.json',reg)
    def apply(self,transaction,hook=lambda _:None):
        d,r=self.journal(transaction)
        try:
            if r['phase']!='prepared' or self.classify(d,r)!={'files':'original','registry':'original'}:raise Refused('not a fresh prepared transaction')
            r['phase']='applying';write_json(d,'journal.json',r);hook('before_rename')
            if self.classify(d,r)!={'files':'original','registry':'original'}:raise Refused('state changed before rename')
            rename(d,'slot',self.apps,r['proposal']['slug'],1 if r['before'] is None else 2);hook('after_rename');os.fsync(d);os.fsync(self.apps)
            if self.classify(d,r)!={'files':'updated','registry':'original'}:raise Refused('uncertain publication state')
            self.registry_set(r,True);hook('after_registry');r['phase']='committed';write_json(d,'journal.json',r);return self.classify(d,r)
        finally:os.close(d)
    def finish_commit(self,transaction):
        d,r=self.journal(transaction)
        try:
            if r['phase']!='applying' or self.classify(d,r)['files']!='updated':raise Refused('no known interrupted publication to finish')
            os.fsync(d);os.fsync(self.apps)
            self.registry_set(r,True);r['phase']='committed';write_json(d,'journal.json',r);return self.classify(d,r)
        finally:os.close(d)
    def rollback(self,transaction,hook=lambda _:None):
        d,r=self.journal(transaction)
        try:
            if r['phase'] not in ('applying','committed','rolling_back'):raise Refused('not rollback eligible')
            state=self.classify(d,r);r['phase']='rolling_back';write_json(d,'journal.json',r)
            if state['files']=='updated':
                hook('before_rollback')
                if self.classify(d,r)['files']!='updated':raise Refused('rollback state changed')
                if r['before'] is None:rename(self.apps,r['proposal']['slug'],d,'slot',1)
                else:rename(d,'slot',self.apps,r['proposal']['slug'],2)
                hook('after_rollback');os.fsync(d);os.fsync(self.apps)
            if self.classify(d,r)['files']!='original':raise Refused('uncertain rollback state')
            os.fsync(d);os.fsync(self.apps)
            self.registry_set(r,False);r['phase']='rolled_back';write_json(d,'journal.json',r);return self.classify(d,r)
        finally:os.close(d)

def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['init-registry','prepare','apply','reconcile','finish-commit','rollback']);p.add_argument('transaction',nargs='?');a=p.parse_args();s=None
    try:
        s=Studio()
        if a.operation=='init-registry':s.init_registry();result={'initialized':True}
        elif a.operation=='prepare':
            data=sys.stdin.buffer.read(65537)
            if len(data)>65536:raise Refused('approval packet too large')
            packet=json.loads(data,object_pairs_hook=unique)
            if not isinstance(packet,dict) or set(packet)!={'proposal','approval_digest'}:raise Refused('approval packet schema')
            result=s.prepare(a.transaction,packet['proposal'],packet['approval_digest'])
        else:result=getattr(s,a.operation.replace('-','_'))(a.transaction)
        print(json.dumps({'ok':True,'result':result}));return 0
    except Exception as e:print(json.dumps({'ok':False,'error':str(e),'next':'Read reconcile state before any retry; unknown states need investigation.'}));return 1
    finally:
        if s:s.close()
if __name__=='__main__':raise SystemExit(main())
