import os,selectors,subprocess,time
from primitives import Refused
HOME="/home/dzfbipjkvhxg"
REPO=HOME+"/repositories/github-transfer-test-20261108"
REMOTE="https://github.com/searchanalystsasikumartalks/my-first-project.git"
def git(args,limit=1048576):
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':HOME,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
    p=subprocess.Popen(['git','--no-replace-objects','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','submodule.recurse=false','-C',REPO]+args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
    sel=selectors.DefaultSelector();data=b'';end=time.monotonic()+20
    try:
        os.set_blocking(p.stdout.fileno(),False);sel.register(p.stdout,selectors.EVENT_READ)
        while True:
            if time.monotonic()>=end:raise Refused('git timeout')
            if not sel.select(.1):continue
            b=os.read(p.stdout.fileno(),min(65536,limit+1-len(data)))
            if not b:break
            data+=b
            if len(data)>limit:raise Refused('git output exceeds bound')
        if p.wait(timeout=max(.01,end-time.monotonic())):raise Refused('git operation failed')
        return data
    finally:
        sel.close();p.stdout.close()
        if p.poll() is None:p.kill()
        p.wait()

