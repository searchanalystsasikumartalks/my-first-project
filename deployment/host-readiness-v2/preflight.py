#!/usr/bin/env python3
"""Read-only host preflight by default. --temporary-test explicitly adds private disposable probes."""
import argparse,ctypes,fcntl,hashlib,json,os,re,stat,subprocess,sys,tempfile
HOME='/home/dzfbipjkvhxg'
APPS=HOME+'/public_html/appln/apps'
PRIVATE=HOME+'/.local/appstudio-deployer'
KNOWN_PYTHON_BIN=HOME+'/virtualenv/sasi-mysql-name-test/sasi-mysql-name-test/3.11/bin'
WRAPPER='/usr/share/l.v.e-manager/utils/python_wrapper'
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW

def directory(path):
    fd=os.open('/',DIR)
    try:
        for p in path.split('/')[1:]:
            if p in ('','.','..'):raise ValueError('noncanonical path')
            n=os.open(p,DIR,dir_fd=fd);os.close(fd);fd=n
        return fd
    except BaseException:os.close(fd);raise

def wrapper_source():
    fd=os.open(WRAPPER,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        result={'path':WRAPPER,'size':st.st_size,'mode':oct(stat.S_IMODE(st.st_mode)),'executed':False}
        if not stat.S_ISREG(st.st_mode):raise ValueError('wrapper is not a regular file')
        if not 0<st.st_size<=65536:
            result['source_status']='size_outside_read_bound';return result
        content=b''
        while len(content)<=65536:
            chunk=os.read(fd,min(8192,65537-len(content)))
            if not chunk:break
            content+=chunk
        after=os.fstat(fd);current=os.stat(WRAPPER,follow_symlinks=False)
        key=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
        if len(content)>65536 or key(st)!=key(after) or key(after)!=key(current):raise ValueError('wrapper changed during bounded read')
        result['sha256']=hashlib.sha256(content).hexdigest()
        if content.startswith(b'\x7fELF'):
            result['source_status']='ELF_binary_not_dumped';return result
        try:text=content.decode('utf-8')
        except UnicodeError:
            result['source_status']='non_UTF8_not_dumped';return result
        if any(ord(c)<32 and c not in '\n\r\t' for c in text) or not text.startswith('#!'):
            result['source_status']='not_text_script_not_dumped';return result
        if re.search(r'password|secret|token|credential|BEGIN .*PRIVATE KEY',text,re.I):
            result['source_status']='potential_sensitive_text_withheld';return result
        result['source_status']='bounded_text_script';result['source']=text;return result
    finally:os.close(fd)

def python_candidates():
    # Metadata only for fixed conventional interpreter names in the verified venv.
    # Resolved targets are reported, never executed or read by this function.
    candidates=[]
    for name in ('python','python3','python3.11','python3.11_bin'):
        path=KNOWN_PYTHON_BIN+'/'+name
        try:st=os.lstat(path)
        except FileNotFoundError:
            candidates.append({'name':name,'exists':False});continue
        item={'name':name,'exists':True,'path':path,'symlink':stat.S_ISLNK(st.st_mode),'mode':oct(stat.S_IMODE(st.st_mode))}
        if stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            item['resolved_path']=os.path.realpath(path)
            item['executable_access']=os.access(path,os.X_OK)
        else:item['unsupported_type']=True
        candidates.append(item)
    return {'known_bin':KNOWN_PYTHON_BIN,'candidates':candidates,'executed':False,'base_interpreter_selected':False}

def git_check():
    env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
    def run(args):
        # Help/version only: not a repository, network operation or config read.
        p=subprocess.run(['/usr/bin/git']+args,cwd='/',env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5)
        if len(p.stdout)>65536:raise ValueError('Git help output unexpectedly large')
        return p.stdout.decode('utf-8','replace')
    version=run(['--version']).strip();helptext=run(['fetch','-h']).replace('--[no-]','--')
    flags=['--refmap','--no-auto-maintenance','--write-commit-graph','--recurse-submodules','--tags']
    # Git help may show the positive form; actual negative-form acceptance remains an execution check.
    checks={f:(f in helptext or (f=='--no-auto-maintenance' and '--auto-maintenance' in helptext)) for f in flags}
    return {'version':version,'help_flags':checks,'all_documented':all(checks.values()),'negative_flag_execution':'not tested; no fetch performed'}

def temporary_probe(homefd,libc):
    # Explicit opt-in creates only a unique mode0700 private temporary directory.
    path=tempfile.mkdtemp(prefix='.appstudio-v2-preflight-',dir=HOME)
    fd=directory(path)
    try:
        if os.fstat(fd).st_dev!=os.fstat(homefd).st_dev:raise ValueError('temporary directory filesystem mismatch')
        for name in ('one','two'):
            x=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
            try:os.write(x,name.encode());os.fsync(x)
            finally:os.close(x)
        lock=os.open('lock',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
        finally:os.close(lock)
        fn=libc.renameat2;fn.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint);fn.restype=ctypes.c_int
        if fn(fd,b'one',fd,b'two',1)!=-1 or ctypes.get_errno()!=17:raise ValueError('NOREPLACE did not refuse existing destination')
        if fn(fd,b'one',fd,b'two',2)!=0:raise OSError(ctypes.get_errno(),'EXCHANGE failed')
        for name,expected in [('one',b'two'),('two',b'one')]:
            f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
            try:
                if os.read(f,16)!=expected:raise ValueError('exchange verification failed')
            finally:os.close(f)
        os.fsync(fd)
        return {'flock':True,'file_fsync':True,'directory_fsync':True,'rename_noreplace':True,'rename_exchange':True}
    finally:
        # Exact probe files only; never recurse or clean an unexpected directory tree.
        for name in ('one','two','lock'):
            try:os.unlink(name,dir_fd=fd)
            except FileNotFoundError:pass
        os.close(fd);os.rmdir(path)

def inspect(temporary=False):
    r={'operation':'appstudio-v2-host-preflight','temporary_test_requested':temporary,'checks':{},'failures':[]}
    def check(name,fn):
        try:r['checks'][name]=fn()
        except Exception as e:r['failures'].append({'check':name,'error':type(e).__name__+': '+str(e)})
    r['checks']['python']={'version':list(sys.version_info[:3]),'supported':sys.version_info>=(3,10),'executable':sys.executable,'resolved_executable':os.path.realpath(sys.executable),'prefix':sys.prefix,'base_prefix':getattr(sys,'base_prefix',sys.prefix),'base_executable':getattr(sys,'_base_executable',None)}
    check('known_python_candidates',python_candidates)
    check('installed_wrapper',wrapper_source)
    if sys.version_info<(3,10):r['failures'].append({'check':'python','error':'Python3.10+ required'})
    libc=ctypes.CDLL(None,use_errno=True);r['checks']['renameat2_symbol']=hasattr(libc,'renameat2')
    if not hasattr(libc,'renameat2'):r['failures'].append({'check':'renameat2','error':'libc symbol unavailable'})
    fds=[]
    try:
        def paths():
            h=directory(HOME);fds.append(h);a=directory(APPS);fds.append(a)
            return {'same_filesystem':os.fstat(h).st_dev==os.fstat(a).st_dev,'home_mode':oct(stat.S_IMODE(os.fstat(h).st_mode)),'apps_mode':oct(stat.S_IMODE(os.fstat(a).st_mode))}
        check('paths',paths)
        def private():
            try:f=directory(PRIVATE)
            except FileNotFoundError:return {'exists':False,'no_state_read':True}
            try:
                st=os.fstat(f);return {'exists':True,'mode':oct(stat.S_IMODE(st.st_mode)),'owned_by_current_user':st.st_uid==os.geteuid(),'owner_only':not bool(st.st_mode&0o077),'no_state_read':True}
            finally:os.close(f)
        check('private_root',private);check('git',git_check)
        if r['checks'].get('git',{}).get('all_documented') is False:r['failures'].append({'check':'git','error':'required flags not documented; actual capability unresolved'})
        pr=r['checks'].get('private_root',{})
        if pr.get('exists') and (not pr.get('owner_only') or not pr.get('owned_by_current_user')):r['failures'].append({'check':'private_root','error':'existing root ownership/mode requires review; not changed'})
        if r['checks'].get('paths',{}).get('same_filesystem') is False:r['failures'].append({'check':'paths','error':'different filesystems'})
        if temporary and fds and hasattr(libc,'renameat2'):check('temporary_probe',lambda:temporary_probe(fds[0],libc))
    finally:
        for f in fds:os.close(f)
    r['ready_for_review']=not r['failures'];r['installed']=False;r['network_tested']=False
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--temporary-test',action='store_true');a=p.parse_args()
    r=inspect(a.temporary_test);print(json.dumps(r,sort_keys=True));return 0 if r['ready_for_review'] else 1
if __name__=='__main__':raise SystemExit(main())
