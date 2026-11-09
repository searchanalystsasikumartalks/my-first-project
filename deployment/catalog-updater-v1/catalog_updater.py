#!/usr/bin/env python3
"""Manual, local Application Studio catalog updater. No web endpoint or network access."""
import argparse, datetime, fcntl, hashlib, json, os, pwd, re, stat, sys, uuid
from pathlib import Path
from catalog_plan import FILES, plan, digest, require, unique_pairs, BASE
from html_checks import Indexability

ACCOUNT_HOME=pwd.getpwuid(os.geteuid()).pw_dir
DEFAULT_ROOT=os.path.join(ACCOUNT_HOME,'public_html','appln')
DEFAULT_STATE=os.path.join(ACCOUNT_HOME,'.appstudio-catalog-updater')
LIMIT=2*1024*1024
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW

def directory(path):
    path=os.path.abspath(path)
    fd=os.open('/',DIR)
    try:
        for part in Path(path).parts[1:]:
            n=os.open(part,DIR,dir_fd=fd);os.close(fd);fd=n
        return fd
    except BaseException:os.close(fd);raise

def readfile(fd,name):
    require('/' not in name and name not in ('.','..'),'Unsafe filename')
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        s=os.fstat(f);require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size<=LIMIT,'Unsafe file')
        data=b''
        while len(data)<=LIMIT:
            b=os.read(f,min(65536,LIMIT+1-len(data)))
            if not b:break
            data+=b
        end=os.fstat(f);named=os.stat(name,dir_fd=fd,follow_symlinks=False)
        identity=lambda a:(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_nlink)
        require(len(data)<=LIMIT and identity(s)==identity(end)==identity(named),'File changed while reading')
        return data,stat.S_IMODE(s.st_mode)
    finally:os.close(f)

def write_new(fd,name,data,mode=0o600):
    f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=fd)
    try:
        while data:data=data[os.write(f,data):]
        os.fchmod(f,mode);os.fsync(f)
    finally:os.close(f)

def h(b):return hashlib.sha256(b).hexdigest()
def decode(b):return b.decode('utf-8')
def loadjson(b):return json.loads(decode(b),object_pairs_hook=unique_pairs)

class Updater:
    def __init__(self,root,state):
        self.root=os.path.abspath(root);self.state=os.path.abspath(state)
        require('public_html' not in Path(self.state).parts,'State/backups must be outside public_html')
        require(not self.state.startswith(self.root+os.sep) and self.state!=self.root,'State must be outside site root')
        self.rootfd=self.statefd=self.lock=None
        try:
            self.rootfd=directory(self.root);self.rootid=self.identity(self.rootfd)
            parent=directory(str(Path(self.state).parent))
            try:
                try:os.mkdir(Path(self.state).name,0o700,dir_fd=parent)
                except FileExistsError:pass
            finally:os.close(parent)
            self.statefd=directory(self.state)
            ss=os.fstat(self.statefd)
            require(ss.st_mode&0o077==0 and ss.st_uid==os.geteuid(),'State directory must be owner-only and owned by current user')
            self.lock=os.open('lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.statefd)
            ls=os.fstat(self.lock);require(stat.S_ISREG(ls.st_mode) and ls.st_nlink==1 and ls.st_uid==os.geteuid(),'Unsafe lock')
            fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:
            self.close();raise
    @staticmethod
    def identity(fd):
        s=os.fstat(fd);return [s.st_dev,s.st_ino]
    def close(self):
        for attr in ('lock','statefd','rootfd'):
            fd=getattr(self,attr,None)
            if fd is not None:os.close(fd);setattr(self,attr,None)
    def check_root(self):
        fd=directory(self.root)
        try:require(self.identity(fd)==self.rootid,'Site directory replaced')
        finally:os.close(fd)
    def snapshot(self):
        self.check_root();return {n:readfile(self.rootfd,n) for n in FILES}
    def candidates(self,explicit=None):
        apps=os.open('apps',DIR,dir_fd=self.rootfd);found=[];skipped=[]
        try:
            if explicit:require(isinstance(explicit.get('slug'),str) and bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',explicit['slug'])), 'Unsafe slug')
            names=[explicit['slug']] if explicit else sorted(os.listdir(apps))
            for slug in names:
                if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):continue
                try:app=os.open(slug,DIR,dir_fd=apps)
                except (NotADirectoryError,OSError):
                    if explicit:raise
                    skipped.append({'slug':slug,'reason':'not a regular app directory'});continue
                try:
                    if explicit:meta=dict(explicit)
                    else:
                        try:meta=loadjson(readfile(app,'app-meta.json')[0])
                        except FileNotFoundError:continue
                        require(isinstance(meta,dict),'Invalid app metadata')
                        if meta.pop('catalog',False) is not True:continue
                        require(meta.get('slug')==slug,'Metadata slug does not match folder')
                    body=readfile(app,'index.html')[0];p=Indexability();p.feed(decode(body))
                    require(not p.noindex,'App declares noindex; excluded from sitemap')
                    url=BASE+'apps/'+slug+'/'
                    require(not p.canonicals or p.canonicals==[url],'Canonical mismatch')
                    found.append((meta,dict(path='apps/'+slug+'/index.html',type='file',bytes=len(body),sha256=h(body))))
                finally:os.close(app)
        finally:os.close(apps)
        return found,skipped
    def build(self,explicit=None):
        before=self.snapshot();current={n:decode(before[n][0]) for n in FILES};found,skipped=self.candidates(explicit)
        for meta,inventory in found:
            p=plan(current,meta,[inventory],{n:digest(current[n]) for n in FILES})
            for w in p['writes']:current[w['path']]=w['content']
        after={n:current[n].encode() for n in FILES}
        return before,after,skipped,found
    def save_journal(self,fd,j):
        name='journal-'+uuid.uuid4().hex+'.tmp';write_new(fd,name,json.dumps(j,sort_keys=True).encode())
        os.replace(name,'journal.json',src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
    def pending(self):
        pending=[]
        for name in os.listdir(self.statefd):
            if not re.fullmatch('run-[a-f0-9]{32}',name):continue
            fd=os.open(name,DIR,dir_fd=self.statefd)
            try:
                try:j=loadjson(readfile(fd,'journal.json')[0])
                except FileNotFoundError:pending.append(name);continue
                if j.get('phase') not in ('complete','rolled-back'):pending.append(name)
            finally:os.close(fd)
        return pending
    def run(self,explicit=None,apply=False,hook=lambda _:None):
        require(not self.pending(),'Unfinished run exists; inspect status and reconcile before a new run')
        before,after,skipped,app_sources=self.build(explicit)
        changed=[n for n in FILES if before[n][0]!=after[n]]
        if not changed:return {'status':'no-op','changed':[],'skipped':skipped}
        if not apply:return {'status':'check-only','changed':changed,'skipped':skipped,'live_changed':False}
        # Validate all original files again before creating durable run records.
        require(self.snapshot()==before,'Catalog changed; nothing applied')
        require(self.candidates(explicit)[0]==app_sources,'App source changed; nothing applied')
        require(all(before[n][1] in (0o600,0o640,0o644) for n in FILES),'Unsupported catalog mode; review permissions separately')
        run='run-'+uuid.uuid4().hex;os.mkdir(run,0o700,dir_fd=self.statefd);os.fsync(self.statefd)
        fd=os.open(run,DIR,dir_fd=self.statefd)
        j={'version':1,'root':self.root,'root_id':self.rootid,'run':run,'phase':'prepared','files':{},'updated':[]}
        try:
            for n in FILES:
                require(before[n][1] in (0o600,0o640,0o644),'Unsupported catalog mode; review permissions separately')
                write_new(fd,'before-'+n,before[n][0]);write_new(fd,'after-'+n,after[n])
                j['files'][n]={'before':h(before[n][0]),'after':h(after[n]),'mode':before[n][1]}
            self.save_journal(fd,j);j['phase']='applying';self.save_journal(fd,j)
            for n in FILES:
                hook('before:'+n);self.check_root()
                require(self.candidates(explicit)[0]==app_sources,'App source changed; stop and reconcile')
                require(readfile(self.rootfd,n)==before[n],'Concurrent edit; stop and reconcile')
                if n in changed:self.replace(n,after[n],before[n][1])
                require(readfile(self.rootfd,n)==(after[n],before[n][1]),'After verification failed')
                j['updated'].append(n);self.save_journal(fd,j);hook('after:'+n)
            j['phase']='complete';self.save_journal(fd,j)
            return {'status':'complete','run':run,'changed':changed,'backup':self.state+'/'+run,'skipped':skipped}
        finally:os.close(fd)
    def replace(self,name,data,mode):
        tmp='.catalog-'+uuid.uuid4().hex+'.tmp'
        write_new(self.rootfd,tmp,data,mode)
        os.replace(tmp,name,src_dir_fd=self.rootfd,dst_dir_fd=self.rootfd);os.fsync(self.rootfd)
    def inspect(self,run,rollback=False):
        require(bool(re.fullmatch('run-[a-f0-9]{32}',run)),'Invalid run ID')
        fd=os.open(run,DIR,dir_fd=self.statefd)
        try:
            j=loadjson(readfile(fd,'journal.json')[0]);self.check_root()
            require(j.get('version')==1 and j.get('root')==self.root and j.get('root_id')==self.rootid and j.get('run')==run and set(j.get('files',{}))==set(FILES),'Journal binding mismatch')
            require(j.get('phase') in ('prepared','applying','complete','rolling-back','rolled-back'),'Invalid journal phase')
            require(isinstance(j.get('updated'),list) and len(set(j['updated']))==len(j['updated']) and all(n in FILES for n in j['updated']),'Invalid journal progress')
            for meta in j['files'].values():
                require(isinstance(meta,dict) and set(meta)=={'before','after','mode'} and type(meta['mode']) is int and meta['mode'] in (0o600,0o640,0o644),'Invalid journal file mode')
                require(all(isinstance(meta[k],str) and re.fullmatch('[a-f0-9]{64}',meta[k]) for k in ('before','after')),'Invalid journal hash')
            state={};backups={}
            for n in FILES:
                b=readfile(fd,'before-'+n)[0];a=readfile(fd,'after-'+n)[0];m=j['files'][n]
                require(h(b)==m['before'] and h(a)==m['after'],'Backup tampered')
                live,mode=readfile(self.rootfd,n)
                require(mode==m['mode'],'Live mode changed; review separately')
                state[n]='original' if live==b else 'updated' if live==a else 'conflict';backups[n]=(b,a)
            if rollback:
                require('conflict' not in state.values(),'External changes detected; rollback refused')
                j['phase']='rolling-back';self.save_journal(fd,j)
                for n in reversed(FILES):
                    self.check_root();b,a=backups[n];live,mode=readfile(self.rootfd,n)
                    require(live in (b,a) and mode==j['files'][n]['mode'],'Concurrent change; rollback stopped')
                    if live!=b:self.replace(n,b,j['files'][n]['mode'])
                    require(readfile(self.rootfd,n)==(b,j['files'][n]['mode']),'Rollback verification failed')
                j['phase']='rolled-back';self.save_journal(fd,j);state={n:'original' for n in FILES}
            return {'run':run,'phase':j['phase'],'files':state}
        finally:os.close(fd)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default=DEFAULT_ROOT);p.add_argument('--state',default=DEFAULT_STATE)
    p.add_argument('action',choices=['check','apply','status','rollback']);p.add_argument('--app-metadata');p.add_argument('--run')
    a=p.parse_args();u=None
    try:
        u=Updater(a.root,a.state)
        if a.action in ('status','rollback'):
            result=u.inspect(a.run,rollback=a.action=='rollback') if a.run else {'pending_runs':u.pending()}
        else:
            meta=loadjson(Path(a.app_metadata).read_bytes()) if a.app_metadata else None
            if meta is not None:meta.pop('catalog',None)
            result=u.run(meta,apply=a.action=='apply')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as e:
        print(json.dumps({'status':'stopped','error':str(e),'instruction':'Do not repeat apply after uncertain outcome. Use status and inspect the saved run.'}));return 1
    finally:
        if u:u.close()
if __name__=='__main__':sys.exit(main())
