"""Trusted installed coordinator; repository supplies data only. Never install from a polled checkout."""
import json,os,re,stat,uuid
from dataclasses import asdict,is_dataclass
import intake,studio
from primitives import Refused
POLICY='automatic-policy.json'
STATE='automatic-state.json'

def policy(raw):
    if not isinstance(raw,dict) or set(raw)!={'version','mode','authority_id','scopes'} or type(raw['version']) is not int or raw['version']!=1 or raw['mode'] not in ('draft','auto'):raise Refused('invalid local policy')
    if not isinstance(raw['authority_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}',raw['authority_id']):raise Refused('local authority reference required')
    if not isinstance(raw['scopes'],list) or len(raw['scopes'])>64:raise Refused('bounded explicit scopes required')
    ids=set();slugs=set()
    for s in raw['scopes']:
        if not isinstance(s,dict) or set(s)!={'app_id','slug','operations'}:raise Refused('invalid scope')
        studio.appid(s['app_id']);studio.slug(s['slug'])
        if s['app_id'] in ids or s['slug'] in slugs:raise Refused('duplicate scope')
        if not isinstance(s['operations'],list) or not s['operations'] or len(set(s['operations']))!=len(s['operations']) or any(x not in ('create','update') for x in s['operations']):raise Refused('invalid scoped operations')
        ids.add(s['app_id']);slugs.add(s['slug'])
    return raw

def permits(p,x):return p['mode']=='auto' and any(s['app_id']==x['app_id'] and s['slug']==x['slug'] and x['operation'] in s['operations'] for s in p['scopes'])
def proposal(m,a):return studio.proposal({'app_id':a.app_id,'slug':a.slug,'display_name':a.display_name,'operation':a.operation,'commit':m.commit,'hashes':dict(a.files),'expected_revision':a.expected_revision})

def validate_state(s):
    if not isinstance(s,dict) or set(s)!={'version','last_tip','draft','attempts'} or s['version']!=1 or type(s['version']) is not int:raise Refused('invalid coordinator state')
    if s['last_tip'] is not None and (not isinstance(s['last_tip'],str) or not re.fullmatch('[a-f0-9]{40}',s['last_tip'])):raise Refused('invalid prior tip')
    if not isinstance(s['attempts'],dict) or len(s['attempts'])>1000:raise Refused('receipt ledger full or invalid')
    if s['draft'] is not None:
        if not isinstance(s['draft'],dict) or set(s['draft'])!={'tip','manifest_sha256','proposals'} or not isinstance(s['draft']['proposals'],list) or len(s['draft']['proposals'])>64:raise Refused('invalid draft record')
        if not isinstance(s['draft']['tip'],str) or not re.fullmatch('[a-f0-9]{40}',s['draft']['tip']) or not isinstance(s['draft']['manifest_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',s['draft']['manifest_sha256']):raise Refused('invalid draft binding')
        for x in s['draft']['proposals']:studio.proposal(x)
    for k,r in s['attempts'].items():
        if not isinstance(r,dict) or set(r)!={'transaction','proposal','policy_digest','authority_id','phase','receipt'} or k!=studio.revision(studio.proposal(r['proposal'])):raise Refused('attempt binding invalid')
        studio.appid(r['transaction'])
        if not isinstance(r['authority_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}',r['authority_id']):raise Refused('invalid attempt authority')
        if r['phase']!='committed' and r['receipt'] is not None:raise Refused('invalid uncommitted receipt')
        if r['phase'] not in ('attempting','uncertain','committed'):raise Refused('invalid attempt phase')
        if not isinstance(r['policy_digest'],str) or not re.fullmatch('[a-f0-9]{64}',r['policy_digest']):raise Refused('invalid authority digest')
        if r['phase']=='committed' and r['receipt']!={'files':'updated','registry':'updated'}:raise Refused('invalid committed receipt')
    return s

class Coordinator:
    def __init__(self,s,poll=intake.poll_and_read,refresh=None):
        self.s=s;self.poll=poll
        if refresh is None:
            from repo_refresh import ensure_objects
            refresh=ensure_objects
        self.refresh=refresh
    def local_policy(self):
        st=os.stat(POLICY,dir_fd=self.s.root,follow_symlinks=False)
        if st.st_uid!=os.geteuid() or st.st_mode&0o077 or not stat.S_ISREG(st.st_mode):raise Refused('policy must be local owner-only regular file')
        return policy(studio.read_json(self.s.root,POLICY,65536))
    def load(self):
        # Missing state is NOT bootstrapped by a scheduled run.
        return validate_state(studio.read_json(self.s.root,STATE))
    def save(self,s):studio.write_json(self.s.root,STATE,validate_state(s))
    def reconcile(self,s):
        for k,r in s['attempts'].items():
            if r['phase']=='committed':continue
            # Never replay prepare/apply on an uncertain attempt, even if no journal exists.
            try:
                d,j=self.s.journal(r['transaction'])
                try:
                    if j['proposal']!=r['proposal'] or j['approval_digest']!=k:raise Refused('attempt journal mismatch')
                    actual=self.s.classify(d,j)
                    if j['phase']!='committed' or actual!={'files':'updated','registry':'updated'}:raise Refused('interrupted action requires explicit operator reconcile/finish/rollback')
                finally:os.close(d)
            except Exception as e:raise Refused('blocked uncertain transaction '+r['transaction']+': '+str(e)) from e
            r['phase']='committed';r['receipt']=actual;self.save(s)
    def cycle(self):
        p=self.local_policy();s=self.load();self.reconcile(s)
        observed=self.poll(previous_commit=s['last_tip'])
        if observed.status=='missing_manifest':return {'status':'missing_manifest','tip':observed.branch_tip}
        m=observed.manifest
        if m is None:raise Refused('missing parsed manifest')
        candidates=[proposal(m,a) for a in m.apps]
        s['draft']={'tip':observed.branch_tip,'manifest_sha256':m.sha256,'proposals':candidates};self.save(s)
        if p['mode']=='draft':return {'status':'draft','count':len(candidates),'tip':observed.branch_tip}
        if any(not permits(p,x) for x in candidates):raise Refused('manifest exceeds explicitly installed auto scope')
        # Fetch objects only; no checkout, build, hooks, or repository scripts executed.
        receipt=self.refresh(observed.branch_tip,m.commit,s['last_tip'])
        if is_dataclass(receipt):receipt=asdict(receipt)
        s['last_tip']=observed.branch_tip;self.save(s)
        completed=0
        for x in candidates:
            key=studio.revision(x)
            if key in s['attempts']:
                if s['attempts'][key]['phase']!='committed':raise Refused('unreconciled attempt')
                continue
            if len(s['attempts'])>=1000:raise Refused('receipt ledger full; archive with review')
            # Detect owner mode/scope withdrawal during poll/fetch, under cooperative writer model.
            if self.local_policy()!=p:raise Refused('local authority changed during cycle')
            txn=str(uuid.uuid4());r={'transaction':txn,'proposal':x,'policy_digest':studio.revision(p),'authority_id':p['authority_id'],'phase':'attempting','receipt':None}
            s['attempts'][key]=r;self.save(s)
            try:
                self.s.prepare(txn,x,key)
                if self.local_policy()!=p:raise Refused('authority changed after preparation')
                actual=self.s.apply(txn)
                if actual!={'files':'updated','registry':'updated'}:raise Refused('publication not verified')
                r['phase']='committed';r['receipt']=actual;self.save(s);completed+=1
            except BaseException:
                r['phase']='uncertain';r['receipt']=None
                self.save(s)
                raise
        return {'status':'completed','new_commits':completed,'tip':observed.branch_tip,'source_commit':m.commit,'fetch':receipt}

def main():
    import argparse,signal
    def expired(*_):raise TimeoutError('coordinator 300-second budget expired; reconcile before retry')
    signal.signal(signal.SIGALRM,expired);signal.alarm(300)
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['init-state','run-once']);a=parser.parse_args();s=None
    try:
        s=studio.Studio()
        if a.operation=='init-state':
            studio.write_json(s.root,STATE,{'version':1,'last_tip':None,'draft':None,'attempts':{}},initial=True);r={'initialized':True}
        else:r=Coordinator(s).cycle()
        print(json.dumps({'ok':True,'result':r}));return 0
    except Exception as e:print(json.dumps({'ok':False,'error':str(e),'next':'No automatic replay. Inspect local state and transaction journal.'}));return 1
    finally:
        signal.alarm(0)
        if s:s.close()
