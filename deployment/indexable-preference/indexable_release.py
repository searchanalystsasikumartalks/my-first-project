#!/usr/bin/env python3
"""One exact four-file indexability release. No unrelated app changes. See README."""
import argparse, ctypes, fcntl, hashlib, json, os, stat, sys, uuid
from pathlib import Path
HOME='/home/dzfbipjkvhxg'
TARGET=HOME+'/public_html/appln'
PRIVATE=HOME+'/.indexable-preference-20261108'
SOURCE=str(Path(__file__).resolve().parent/'files')
FILES=('apps/a/index.html', 'index.html', 'manifest.json', 'sitemap.xml')
SLOTS={n:'slot-'+n.replace('/','__') for n in FILES}
BEFORE={'apps/a/index.html': '87de9c392ecbc07ba17dd02cdcc5c278837744aab73591a3a7dda4beb147e96f', 'index.html': 'eb9bca790a93d7f46785f8bce9a54d79e1fa5fda03783367fcab56529a875b34', 'manifest.json': '963de4eed29ee942f72d696ef406a0405e0472f26e22e02925f229a8494aed5a', 'sitemap.xml': 'bf32caf22874f27c669bab431d21bf4b9a9d8557a2444ce01a66d43d41ba352f'}
AFTER={'apps/a/index.html': 'ba8dcc089ea653eace2b21d87d9a5e1fc2c8dd322070c46010ca76a89614d4e7', 'index.html': '6459dbc288d94a19821d60bacb56f2d6cc0a2f6f8dff4665cf69dff38298ba3d', 'manifest.json': '399f0081f800fc8ae2c7da2a910e19d8a8b8977061ca7f7ffc6928952ce90338', 'sitemap.xml': 'b01643461f86bcc6032b16ba38ab5856abddc4bf3f778226e342d468c468c08c'}
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
class Refused(RuntimeError):pass

def directory(path):
    if not path.startswith('/') or any(p in ('','.','..') for p in path.split('/')[1:]):raise Refused('noncanonical path')
    fd=os.open('/',DIR)
    try:
        for p in path.split('/')[1:]:n=os.open(p,DIR,dir_fd=fd);os.close(fd);fd=n
        return fd
    except BaseException:os.close(fd);raise

def identity(fd):
    s=os.fstat(fd);return [s.st_dev,s.st_ino]

def location(fd,name):
    if name not in FILES and name not in SLOTS.values() and name!='journal.json':raise Refused('unexpected filename')
    parent=os.dup(fd)
    try:
        parts=name.split('/')
        for part in parts[:-1]:n=os.open(part,DIR,dir_fd=parent);os.close(parent);parent=n
        return parent,parts[-1]
    except BaseException:os.close(parent);raise

def parent_ids(fd):
    apps=os.open('apps',DIR,dir_fd=fd)
    try:app=os.open('a',DIR,dir_fd=apps)
    finally:os.close(apps)
    try:return {'.':identity(fd),'apps/a':identity(app)}
    finally:os.close(app)

def snapshot(fd,name,limit=1048576):
    parent,base=location(fd,name)
    try:f=os.open(base,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    except BaseException:os.close(parent);raise
    try:
        before=os.fstat(f)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:raise Refused('bounded regular singly-linked file required')
        data=b''
        while len(data)<=limit:
            b=os.read(f,min(65536,limit+1-len(data)))
            if not b:break
            data+=b
        if len(data)>limit:raise Refused('file exceeds bound')
        after=os.fstat(f);named=os.stat(base,dir_fd=parent,follow_symlinks=False)
        key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if key(before)!=key(after) or key(after)!=key(named):raise Refused('file changed while read')
        return {'identity':[after.st_dev,after.st_ino],'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':stat.S_IMODE(after.st_mode)},data
    finally:os.close(f);os.close(parent)

def durable_file(fd,name,data,mode=0o600):
    f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        while data:data=data[os.write(f,data):]
        os.fchmod(f,mode);os.fsync(f)
    finally:os.close(f)

def exchange(leftfd,left,rightfd,right):
    libc=ctypes.CDLL(None,use_errno=True);fn=libc.renameat2
    fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];fn.restype=ctypes.c_int
    lp,ln=location(leftfd,left);rp,rn=location(rightfd,right)
    try:
        if fn(lp,ln.encode(),rp,rn.encode(),2):raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
        os.fsync(lp);os.fsync(rp)
    finally:os.close(lp);os.close(rp)

def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise Refused('duplicate JSON key')
        out[k]=v
    return out

class Release:
    def __init__(self):
        self.target=directory(TARGET);self.parent=parent_ids(self.target);self.private=directory(PRIVATE)
        if os.fstat(self.private).st_mode&0o077:raise Refused('private backup directory must be owner-only')
        self.lock=os.open('lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.private)
        s=os.fstat(self.lock)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise Refused('unsafe lock')
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def close(self):
        for fd in (self.lock,self.private,self.target):os.close(fd)
    def parent_check(self):
        f=directory(TARGET)
        try:
            if parent_ids(f)!=self.parent:raise Refused('target parent replaced')
        finally:os.close(f)
    def save(self,r):
        tmp='journal.tmp-'+uuid.uuid4().hex
        durable_file(self.private,tmp,json.dumps(r,sort_keys=True,separators=(',',':')).encode())
        os.rename(tmp,'journal.json',src_dir_fd=self.private,dst_dir_fd=self.private);os.fsync(self.private)
    def read(self):
        _,data=snapshot(self.private,'journal.json',65536);r=json.loads(data,object_pairs_hook=pairs)
        if not isinstance(r,dict) or set(r)!={'version','release','parent','phase','before','after'} or type(r['version'])is not int or r['version']!=1 or r['release']!='indexable-preference-20261108' or r['parent']!=self.parent or r['phase'] not in ('prepared','applying','completed','rolling_back','rolled_back'):raise Refused('journal binding invalid')
        for key,expected in [('before',BEFORE),('after',AFTER)]:
            if not isinstance(r[key],dict) or set(r[key])!=set(FILES):raise Refused('journal filenames invalid')
            for n,m in r[key].items():
                if not isinstance(m,dict) or set(m)!={'identity','sha256','size','mode'} or m['sha256']!=expected[n] or type(m['size'])is not int or not 0<=m['size']<=1048576 or m['mode']!=0o644:raise Refused('journal content invalid')
                if not isinstance(m['identity'],list) or len(m['identity'])!=2 or any(type(v)is not int or v<0 for v in m['identity']) or m['identity'][1]==0:raise Refused('journal identity invalid')
        return r
    def state(self,r):
        self.parent_check();out={}
        for n in FILES:
            live,_=snapshot(self.target,n);slot,_=snapshot(self.private,SLOTS[n])
            if live==r['before'][n] and slot==r['after'][n]:out[n]='original'
            elif live==r['after'][n] and slot==r['before'][n]:out[n]='updated'
            else:raise Refused('unexpected state in '+n+'; no automatic overwrite')
        return out
    def apply(self,hook=lambda _:None):
        r=self.read()
        if r['phase']!='prepared' or any(s!='original' for s in self.state(r).values()):raise Refused('not a fresh exact prepared release')
        r['phase']='applying';self.save(r)
        for n in FILES:
            hook('before:'+n)
            if self.state(r)[n]!='original':raise Refused('state changed before exchange')
            exchange(self.private,SLOTS[n],self.target,n);hook('after:'+n)
            os.fsync(self.target);os.fsync(self.private)
            if self.state(r)[n]!='updated':raise Refused('uncertain file replacement')
            self.save(r)
        r['phase']='completed';self.save(r);return self.state(r)
    def rollback(self,hook=lambda _:None):
        r=self.read()
        if r['phase'] not in ('applying','completed','rolling_back'):raise Refused('release not rollback eligible')
        self.state(r);r['phase']='rolling_back';self.save(r)
        for n in reversed(FILES):
            hook('rollback-before:'+n)
            states=self.state(r)
            if states[n]=='updated':
                exchange(self.private,SLOTS[n],self.target,n);hook('rollback-after:'+n)
                os.fsync(self.target);os.fsync(self.private)
                if self.state(r)[n]!='original':raise Refused('uncertain rollback')
                self.save(r)
        os.fsync(self.target);os.fsync(self.private)
        app_parent,unused=location(self.target,'apps/a/index.html')
        try:os.fsync(app_parent)
        finally:os.close(app_parent)
        r['phase']='rolled_back';self.save(r);return self.state(r)

def prepare():
    target=directory(TARGET);source=directory(SOURCE);home=directory(HOME)
    try:
        before={};contents={}
        # Validate ALL FOUR raw current files and proposals before any public mutation.
        for n in FILES:
            before[n],_=snapshot(target,n)
            if before[n]['sha256']!=BEFORE[n] or before[n]['mode']!=0o644:raise Refused('actual live before hash/mode mismatch: '+n)
            meta,contents[n]=snapshot(source,n)
            if meta['sha256']!=AFTER[n]:raise Refused('proposed hash mismatch: '+n)
        os.mkdir('.indexable-preference-20261108',0o700,dir_fd=home);os.fsync(home)
        private=directory(PRIVATE)
        try:
            if os.fstat(private).st_dev!=os.fstat(target).st_dev:raise Refused('same filesystem required')
            after={}
            for n in FILES:
                durable_file(private,SLOTS[n],contents[n],0o644);after[n],_=snapshot(private,SLOTS[n])
            r={'version':1,'release':'indexable-preference-20261108','parent':parent_ids(target),'phase':'prepared','before':before,'after':after}
            durable_file(private,'journal.json',json.dumps(r,sort_keys=True,separators=(',',':')).encode());os.fsync(private)
        finally:os.close(private)
        return r
    finally:
        os.close(home);os.close(source);os.close(target)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','apply','reconcile','rollback','prepare-and-apply']);args=p.parse_args();r=None
    try:
        if args.action in ('prepare','prepare-and-apply'):
            result=prepare()
            if args.action=='prepare':print(json.dumps({'ok':True,'phase':'prepared'}));return 0
        r=Release()
        result=r.state(r.read()) if args.action=='reconcile' else r.rollback() if args.action=='rollback' else r.apply()
        print(json.dumps({'ok':True,'files':result,'backup':PRIVATE}));return 0
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc),'instruction':'Do not retry apply blindly. Inspect with reconcile; rollback only the exact recorded unchanged files.'}));return 1
    finally:
        if r:r.close()
if __name__=='__main__':raise SystemExit(main())
