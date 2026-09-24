"""T1 pilot: bounded pair count per rung to measure real throughput, plus the M=1 control."""
import importlib.util, json, sys, time, os
from pathlib import Path
import itertools
import numpy as np

ROOT = Path("/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade")
sys.path.insert(0, str(ROOT/"src"))
OUT = ROOT/"artifacts/_project/intermediate"

spec = importlib.util.spec_from_file_location("t1", ROOT/"scripts/t1_lower_side_at_M.py")
t1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(t1)
from eibo.statcore import tv_lower_bound

N_PAIRS = int(os.environ.get("T1_PAIRS", "12"))
RUNGS = [int(x) for x in os.environ.get("T1_RUNGS", "1,2").split(",")]

counts = {}
for m in RUNGS:
    c = json.load(open(OUT/("t1_m%d_rung_counts.json"%m)))["counts"]
    counts[m] = {int(s):{int(k):v for k,v in d.items()} for s,d in c.items()}

svcs = t1.gate_services([counts[m] for m in RUNGS])
print("gated services: %d"%len(svcs), flush=True)
pairs = list(itertools.combinations(svcs,2))[:N_PAIRS]
print("pilot pairs: %d, rungs: %s"%(len(pairs),RUNGS), flush=True)

out = {}
for m in RUNGS:
    rng = np.random.default_rng(t1.SAMPLE_SEED)
    idx = {s: t1.onehot_sampled(counts[m], s, m, rng) for s in svcs}
    width = (2*m)**K if (K:=t1.K) else (2*m)**t1.K
    width = (2*m)**t1.K
    t0=time.time(); vals=[]
    for a,b in pairs:
        ia,_ = idx[a]; ib,_ = idx[b]
        Xa=np.zeros((len(ia),width),dtype=np.float32); Xa[np.arange(len(ia)),ia]=1.0
        Xb=np.zeros((len(ib),width),dtype=np.float32); Xb[np.arange(len(ib)),ib]=1.0
        lo,_ = tv_lower_bound(Xa,Xb,alpha=0.025,random_state=0,method="michel")
        vals.append(float(lo))
    el=time.time()-t0
    out["M=%d"%m] = {"width":width,"pairs":len(vals),"seconds":round(el,1),
                     "sec_per_pair":round(el/len(vals),2),
                     "eps_lo_median":float(np.median(vals)),
                     "eps_lo_min":float(min(vals)),"eps_lo_max":float(max(vals))}
    print(json.dumps(out["M=%d"%m]), flush=True)
json.dump(out, open(OUT/"t1_pilot.json","w"), indent=1, sort_keys=True)
print("wrote t1_pilot.json", flush=True)
