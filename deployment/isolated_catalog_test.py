#!/usr/bin/env python3
"""Isolated host test. Website opened read-only; updater only receives private copies."""
import hashlib,json,os,pwd,stat,sys,tempfile
from pathlib import Path
from catalog_updater import Updater,directory,readfile,write_new,loadjson,FILES,DIR
def main():
    home=pwd.getpwuid(os.geteuid()).pw_dir
    source=os.path.join(home,"public_html","appln")
    fd=directory(source)
    appfd=None
    u=None
    try:
        source_identity=Updater.identity(fd)
        before={n:readfile(fd,n) for n in FILES}
        apps=os.open("apps",DIR,dir_fd=fd)
        try:appfd=os.open("rocket-launch-lab",DIR,dir_fd=apps)
        finally:os.close(apps)
        app_identity=Updater.identity(appfd)
        rocket=readfile(appfd,"index.html")
        work=tempfile.mkdtemp(prefix=".catalog-isolated-test-",dir=home)
        if "public_html" in Path(work).parts:raise ValueError("Scratch must be private")
        root=Path(work)/"site";root.mkdir(mode=0o700)
        (root/"apps").mkdir(mode=0o700)
        (root/"apps"/"rocket-launch-lab").mkdir(mode=0o700)
        out=directory(str(root))
        try:
            for n,(data,mode) in before.items():write_new(out,n,data,mode)
        finally:os.close(out)
        out=directory(str(root/"apps"/"rocket-launch-lab"))
        try:write_new(out,"index.html",rocket[0],rocket[1])
        finally:os.close(out)
        meta=loadjson((Path(__file__).parent/"catalog-updater-v1"/"rocket.json").read_bytes())
        u=Updater(str(root),str(Path(work)/"state"))
        result=u.run(meta,apply=True)
        if result.get("status")!="complete" or set(result.get("changed",[]))!=set(FILES):
            raise ValueError("Expected three scratch changes; inspect private test")
        applied=u.snapshot()
        if any(applied[n][0]==before[n][0] for n in FILES):raise ValueError("Scratch update missing")
        repeat=u.run(meta,apply=True)
        if repeat.get("status")!="no-op":raise ValueError("Repeat was not idempotent")
        rollback=u.inspect(result["run"],rollback=True)
        if rollback["phase"]!="rolled-back" or u.snapshot()!=before:raise ValueError("Rollback mismatch")
        if {n:readfile(fd,n) for n in FILES}!=before or readfile(appfd,"index.html")!=rocket:
            raise ValueError("Live source changed during test; outcome requires review")
        fresh=directory(source)
        try:
            if Updater.identity(fresh)!=source_identity:raise ValueError("Live root replaced")
            freshapps=os.open("apps",DIR,dir_fd=fresh)
            try:freshapp=os.open("rocket-launch-lab",DIR,dir_fd=freshapps)
            finally:os.close(freshapps)
            try:
                if Updater.identity(freshapp)!=app_identity or readfile(freshapp,"index.html")!=rocket:raise ValueError("Rocket changed")
                if {n:readfile(fresh,n) for n in FILES}!=before:raise ValueError("Source readback mismatch")
            finally:os.close(freshapp)
        finally:os.close(fresh)
        receipt={"test_id":Path(work).name,"status":"isolated-test-passed","apply":"complete","repeat":"no-op","rollback":"exact-original","live_writes_performed":False,"source_readback_matches":True,"scope":"private scratch only","live_before_sha256":{n:hashlib.sha256(before[n][0]).hexdigest() for n in FILES}}
        report=directory(work)
        try:write_new(report,"receipt.json",json.dumps(receipt,indent=2).encode())
        finally:os.close(report)
        print(json.dumps(receipt,indent=2))
    finally:
        if u:u.close()
        if appfd is not None:os.close(appfd)
        os.close(fd)
if __name__=="__main__":main()
