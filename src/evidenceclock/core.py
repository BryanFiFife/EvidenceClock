from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json, os
from pathlib import Path
from typing import Any

class EvidenceClockError(ValueError): pass

def parse_time(value:str)->datetime:
    if not isinstance(value,str) or not value.strip(): raise EvidenceClockError("timestamp must be a non-empty ISO-8601 string")
    s=value.strip()
    if s.endswith("Z"): s=s[:-1]+"+00:00"
    try: dt=datetime.fromisoformat(s)
    except ValueError as e: raise EvidenceClockError(f"invalid timestamp: {value}") from e
    if dt.tzinfo is None: raise EvidenceClockError("timestamp must include a timezone")
    return dt.astimezone(timezone.utc)

def fmt_time(dt:datetime)->str: return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def hash_file(path:str|Path)->str:
    p=Path(path)
    try: st=p.lstat()
    except OSError as e: raise EvidenceClockError(f"cannot stat file {p}: {e}") from e
    if p.is_symlink(): raise EvidenceClockError(f"refusing symlink evidence: {p}")
    if not p.is_file(): raise EvidenceClockError(f"evidence path is not a regular file: {p}")
    h=sha256()
    try:
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    except OSError as e: raise EvidenceClockError(f"cannot read file {p}: {e}") from e
    return h.hexdigest()

def capture_file(path:str|Path,node_id:str,max_age_seconds:int,observed_at:datetime|None=None)->dict[str,Any]:
    if not isinstance(max_age_seconds,int) or isinstance(max_age_seconds,bool) or max_age_seconds<0: raise EvidenceClockError("max_age_seconds must be an integer >= 0")
    if not isinstance(node_id,str) or not node_id.strip(): raise EvidenceClockError("node_id must be non-empty")
    p=Path(path).resolve(); obs=observed_at or datetime.now(timezone.utc)
    return {"id":node_id.strip(),"observed_at":fmt_time(obs),"max_age_seconds":max_age_seconds,"sha256":hash_file(p),"file":str(p),"depends_on":[]}

@dataclass(frozen=True)
class NodeStatus:
    id:str; fresh:bool; expires_at:str; reasons:tuple[str,...]; effective_sources:tuple[str,...]
    def to_dict(self):
        d=asdict(self); d['reasons']=list(self.reasons); d['effective_sources']=list(self.effective_sources); return d
@dataclass(frozen=True)
class Verification:
    decision_id:str; fresh:bool; checked_at:str; roots:tuple[str,...]; nodes:tuple[NodeStatus,...]; reasons:tuple[str,...]
    def to_dict(self):
        return {"decision_id":self.decision_id,"fresh":self.fresh,"checked_at":self.checked_at,"roots":list(self.roots),"nodes":[n.to_dict() for n in self.nodes],"reasons":list(self.reasons)}

def _normalize(manifest:dict[str,Any]):
    if not isinstance(manifest,dict): raise EvidenceClockError("manifest must be an object")
    decision_id=manifest.get('decision_id','decision')
    if not isinstance(decision_id,str) or not decision_id.strip(): raise EvidenceClockError("decision_id must be non-empty")
    raw_nodes=manifest.get('nodes')
    if not isinstance(raw_nodes,list) or not raw_nodes: raise EvidenceClockError("nodes must be a non-empty list")
    nodes={}
    for raw in raw_nodes:
        if not isinstance(raw,dict): raise EvidenceClockError("each node must be an object")
        nid=raw.get('id')
        if not isinstance(nid,str) or not nid.strip(): raise EvidenceClockError("node id must be non-empty")
        nid=nid.strip()
        if nid in nodes: raise EvidenceClockError(f"duplicate node id: {nid}")
        ttl=raw.get('max_age_seconds')
        if not isinstance(ttl,int) or isinstance(ttl,bool) or ttl<0: raise EvidenceClockError(f"{nid}: max_age_seconds must be integer >= 0")
        deps=raw.get('depends_on',[])
        if not isinstance(deps,list) or any(not isinstance(x,str) or not x.strip() for x in deps): raise EvidenceClockError(f"{nid}: depends_on must be a list of strings")
        expected=raw.get('sha256')
        if expected is not None and (not isinstance(expected,str) or len(expected)!=64 or any(c not in '0123456789abcdefABCDEF' for c in expected)): raise EvidenceClockError(f"{nid}: sha256 must be 64 hex characters")
        file=raw.get('file')
        if file is not None and not isinstance(file,str): raise EvidenceClockError(f"{nid}: file must be a string")
        nodes[nid]={"id":nid,"observed_at":parse_time(raw.get('observed_at')),"max_age_seconds":ttl,"depends_on":tuple(dict.fromkeys(x.strip() for x in deps)),"sha256":expected.lower() if expected else None,"file":file}
    for n in nodes.values():
        for dep in n['depends_on']:
            if dep not in nodes: raise EvidenceClockError(f"{n['id']}: missing dependency {dep}")
    roots=manifest.get('roots') or [raw_nodes[-1].get('id')]
    if not isinstance(roots,list) or not roots or any(not isinstance(x,str) or x not in nodes for x in roots): raise EvidenceClockError("roots must reference existing node ids")
    skew=manifest.get('max_clock_skew_seconds',30)
    if not isinstance(skew,int) or isinstance(skew,bool) or skew<0: raise EvidenceClockError("max_clock_skew_seconds must be integer >= 0")
    return decision_id.strip(),nodes,tuple(dict.fromkeys(roots)),skew

def verify_manifest(manifest:dict[str,Any],at:datetime|None=None,verify_files:bool=True)->Verification:
    decision_id,nodes,roots,skew=_normalize(manifest); now=(at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    visiting=set(); done={}; statuses={}
    def visit(nid):
        if nid in done:return done[nid]
        if nid in visiting: raise EvidenceClockError(f"dependency cycle detected at {nid}")
        visiting.add(nid); n=nodes[nid]
        depvals=[visit(d) for d in n['depends_on']]
        own_exp=n['observed_at']+timedelta(seconds=n['max_age_seconds'])
        eff_exp=min([own_exp]+[d[0] for d in depvals])
        reasons=[]; sources={nid}
        for exp,fresh,rs,src in depvals:
            sources.update(src)
            if not fresh: reasons.append(f"dependency stale: {next(iter(src)) if src else 'unknown'}")
        if n['observed_at']>now+timedelta(seconds=skew): reasons.append("observed_at is too far in the future")
        if now>eff_exp: reasons.append(f"expired at {fmt_time(eff_exp)}")
        if verify_files and n['file']:
            if not n['sha256']: reasons.append("file is configured without sha256")
            else:
                try: actual=hash_file(n['file'])
                except EvidenceClockError as e: reasons.append(str(e))
                else:
                    if actual!=n['sha256']: reasons.append("file digest changed")
        fresh=not reasons
        val=(eff_exp,fresh,tuple(sorted(set(reasons))),frozenset(sources)); done[nid]=val; visiting.remove(nid); return val
    for r in roots: visit(r)
    for nid in nodes: visit(nid)
    for nid in sorted(nodes):
        exp,fresh,rs,src=done[nid]; statuses[nid]=NodeStatus(nid,fresh,fmt_time(exp),rs,tuple(sorted(src)))
    reasons=[]
    for r in roots:
        if not done[r][1]: reasons.append(f"root {r} is stale")
    return Verification(decision_id,not reasons,fmt_time(now),roots,tuple(statuses[k] for k in sorted(statuses)),tuple(reasons))

def load_manifest(path:str|Path)->dict[str,Any]:
    try: data=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as e: raise EvidenceClockError(str(e)) from e
    if not isinstance(data,dict): raise EvidenceClockError("top-level JSON must be an object")
    return data
