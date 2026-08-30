from __future__ import annotations
import argparse,json,sys
from datetime import datetime,timezone
from .core import EvidenceClockError,capture_file,load_manifest,parse_time,verify_manifest

def main(argv=None):
    p=argparse.ArgumentParser(prog='evidenceclock',description='Transitive evidence freshness for AI agents'); sub=p.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('verify'); v.add_argument('manifest'); v.add_argument('--at'); v.add_argument('--no-file-check',action='store_true'); v.add_argument('--json',action='store_true')
    c=sub.add_parser('capture-file'); c.add_argument('path'); c.add_argument('--id',required=True); c.add_argument('--ttl',type=int,required=True)
    ns=p.parse_args(argv)
    try:
        if ns.cmd=='capture-file': print(json.dumps(capture_file(ns.path,ns.id,ns.ttl),indent=2,sort_keys=True)); return 0
        at=parse_time(ns.at) if ns.at else None; r=verify_manifest(load_manifest(ns.manifest),at=at,verify_files=not ns.no_file_check)
        if ns.json: print(json.dumps(r.to_dict(),indent=2,sort_keys=True))
        else:
            print(f"decision={r.decision_id} checked_at={r.checked_at}"); print('FRESH' if r.fresh else 'STALE')
            for n in r.nodes:
                state='fresh' if n.fresh else 'stale'; print(f"  {n.id}: {state}, expires={n.expires_at}")
                for reason in n.reasons: print(f"    - {reason}")
        return 0 if r.fresh else 2
    except EvidenceClockError as e: print(f"evidenceclock: {e}",file=sys.stderr); return 3
if __name__=='__main__': raise SystemExit(main())
