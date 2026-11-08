#!/bin/bash
set -euo pipefail
# Create-only. No package installation, credentials, overwrites or other app edits.
command -v python3 >/dev/null || { echo 'BLOCKED: existing python3 required; nothing deployed.' >&2; exit 1; }
command -v git >/dev/null || { echo 'BLOCKED: existing git required; nothing deployed.' >&2; exit 1; }
exec python3 -I - <<'PY'
import ctypes, hashlib, os, pathlib, selectors, stat, subprocess, sys, tempfile, time
HOME='/home/dzfbipjkvhxg'
REPO=HOME+'/repositories/github-transfer-test-20261108'
PARENT=HOME+'/public_html/appln/apps'
COMMIT='df52a8124715b5fa1d19c38566a620d63fecfec1'
SOURCE='deployment-tests/preference-garden-reflections'
HASHES={
 'app.js':'340eecc739ddc461044356c24ee22782c0781b5aec54ac192826e7a8f04d3e84',
 'data.js':'10dd3e04285aadd6f266fbeeae69f97ba547faad2400d1dff24fdf373cf04769',
 'index.html':'87de9c392ecbc07ba17dd02cdcc5c278837744aab73591a3a7dda4beb147e96f',
 'style.css':'04e7be79e0947524c1c48925227c35b7862761acb622dbb34c9ba1a0eb3f40c3',
}
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
fds=[];stage=None;published=False

def directory(path):
    if not path.startswith('/') or str(pathlib.PurePosixPath(path))!=path:raise RuntimeError('noncanonical directory')
    fd=os.open('/',DIR)
    try:
        for component in path.split('/')[1:]:
            if component in ('','.','..'):raise RuntimeError('unsafe directory component')
            nxt=os.open(component,DIR,dir_fd=fd);os.close(fd);fd=nxt
        return fd
    except BaseException:os.close(fd);raise

def ident(fd):
    s=os.fstat(fd);return (s.st_dev,s.st_ino)

def verify_parent(fd):
    check=directory(PARENT)
    try:
        if ident(check)!=ident(fd):raise RuntimeError('destination parent changed')
    finally:os.close(check)

def git_bytes(args,limit=1048576):
    proc=subprocess.Popen(['git','-C',REPO]+args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    sel=selectors.DefaultSelector();data=b'';deadline=time.monotonic()+15
    try:
        os.set_blocking(proc.stdout.fileno(),False);sel.register(proc.stdout,selectors.EVENT_READ)
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise RuntimeError('Git read timed out')
            if not sel.select(min(remaining,0.25)):continue
            chunk=os.read(proc.stdout.fileno(),min(65536,limit+1-len(data)))
            if not chunk:break
            data+=chunk
            if len(data)>limit:raise RuntimeError('Git object exceeds size limit')
        if proc.wait(timeout=max(0.01,deadline-time.monotonic()))!=0:raise RuntimeError('pinned Git object unavailable')
        return data
    finally:
        sel.close();proc.stdout.close()
        if proc.poll() is None:proc.kill()
        proc.wait()

try:
    libc=ctypes.CDLL(None,use_errno=True)
    rename=libc.renameat2
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    parent=directory(PARENT);fds.append(parent)
    home=directory(HOME);fds.append(home)
    repo=directory(REPO);fds.append(repo)
    try:os.stat('a',dir_fd=parent,follow_symlinks=False)
    except FileNotFoundError:pass
    else:raise RuntimeError('destination a already exists; create-only deployment refused')
    # Git object reads are pinned: the current branch may also contain this deploy recipe.
    git_bytes(['cat-file','-e',COMMIT+'^{commit}'],1024)
    stage=tempfile.mkdtemp(prefix='.appln-a-stage-',dir=HOME)
    stagefd=directory(stage);fds.append(stagefd)
    os.mkdir('payload',0o755,dir_fd=stagefd)
    payload=os.open('payload',DIR,dir_fd=stagefd);fds.append(payload)
    os.fchmod(payload,0o755)
    if os.fstat(payload).st_dev!=os.fstat(parent).st_dev:raise RuntimeError('staging and destination are different filesystems')
    for name,want in HASHES.items():
        data=git_bytes(['show',COMMIT+':'+SOURCE+'/'+name])
        if len(data)>1048576 or b'\0' in data:raise RuntimeError('source file invalid')
        data.decode('utf-8')
        if hashlib.sha256(data).hexdigest()!=want:raise RuntimeError('pinned source hash mismatch: '+name)
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=payload)
        try:
            view=memoryview(data)
            while view:view=view[os.write(fd,view):]
            os.fchmod(fd,0o644);os.fsync(fd)
        finally:os.close(fd)
    os.fsync(payload);os.fsync(stagefd)
    verify_parent(parent)
    # Linux atomic create-only rename. EEXIST, ENOSYS, EXDEV etc. fail closed.
    if rename(stagefd,b'payload',parent,b'a',1)!=0:
        err=ctypes.get_errno();raise OSError(err,os.strerror(err))
    published=True
    os.fsync(parent);os.fsync(stagefd)
    verify_parent(parent)
    live=os.open('a',DIR,dir_fd=parent);fds.append(live)
    if ident(live)!=ident(payload):raise RuntimeError('destination identity changed after rename')
    if sorted(os.listdir(live))!=sorted(HASHES):raise RuntimeError('unexpected deployed files')
    for name,want in HASHES.items():
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=live)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>1048576:raise RuntimeError('unsafe deployed file')
            data=b''
            while True:
                part=os.read(fd,65536)
                if not part:break
                data+=part
                if len(data)>1048576:raise RuntimeError('post-deployment file too large')
            after=os.fstat(fd);named=os.stat(name,dir_fd=live,follow_symlinks=False)
            stamp=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_nlink)
            if stamp(before)!=stamp(after) or stamp(after)!=stamp(named):raise RuntimeError('deployed file changed during verification')
            if hashlib.sha256(data).hexdigest()!=want:raise RuntimeError('post-deployment hash mismatch')
        finally:os.close(fd)
    if sorted(os.listdir(live))!=sorted(HASHES):raise RuntimeError('deployed file set changed')
    verify_parent(parent)
    os.rmdir(stage)
    print('CREATED and verified: '+PARENT+'/a; source commit '+COMMIT)
except Exception as exc:
    print(('UNCERTAIN AFTER RENAME; inspect, do not retry: ' if published else 'BLOCKED; no target rename completed: ')+str(exc),file=sys.stderr)
    if stage:print('Private staging retained if present: '+stage,file=sys.stderr)
    sys.exit(1)
finally:
    for fd in reversed(fds):os.close(fd)
PY
