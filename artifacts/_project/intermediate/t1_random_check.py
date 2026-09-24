"""T1 robustness: is the 990/990 lower-side result an artefact of pair ORDER?

The full M=2 run processed itertools.combinations in lexicographic order: all pairs of
service 0 first, then service 1, etc. Services differ in flow count, so if the lower
bound tracked flow count, an order-correlated result could be masked. Re-run a RANDOM
subsample of M=2 pairs and compare its per-pair values against the same pairs in the
full run, plus report the lower-gate rate for the random subsample.
"""
import importlib.util, json, sys, time
from pathlib import Path
import numpy as np
ROOT=Path("/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade")
sys.path.insert(0,str(ROOT/"src"))
OUT=ROOT/"artifacts/_project/intermediate"
spec=importlib.util.spec_from_file_location("t1",ROOT/"scripts/t1_lower_side_at_M.py")
t1=importlib.util.module_from_spec(spec); spec.loader.exec_module(t1)
from eibo.statcore import tv_lower_bound

N=int(__import__("os").environ.get("N_PAIRS","60"))
SEED=99
c={int(s):{int(k):v for k,v in d.items()} for s,d in json.load(open(OUT/"t1_m2_rung_counts.json"))["counts"].items()}
svcs=t1.gate_services([c])
full={(r['service_a'],r['service_b']):r['eps_lo'] for r in json.load(open(OUT/"t1_lower_side_M2.json"))['rows']}
rng=np.random.default_rng(t1.SAMPLE_SEED); idx={s:t1.onehot_sampled(c,s,2,rng) for s in svcs}
import itertools
allp=list(itertools.combinations(svcs,2))
pick=rng.choice(len(allp), size=N, replace=False)
W=1024
rows=[]
t0=time.time()
for j in pick:
    a,b=allp[j]
    ia,_=idx[a]; ib,_=idx[b]
    Xa=np.zeros((len(ia),W),dtype=np.float32); Xa[np.arange(len(ia)),ia]=1.0
    Xb=np.zeros((len(ib),W),dtype=np.float32); Xb[np.arange(len(ib)),ib]=1.0
    lo,_=tv_lower_bound(Xa,Xb,alpha=0.025,random_state=0,method="michel")
    rows.append(dict(service_a=a,service_b=b,eps_lo=float(lo),full_eps_lo=full[(a,b)]))
v=np.array([r['eps_lo'] for r in rows]); f=np.array([r['full_eps_lo'] for r in rows])
out=dict(check='random-subsample reproducibility vs full M=2 run', seed=int(SEED), pairs=len(rows),
         seconds=round(time.time()-t0,1),
         random_sub_median=float(np.median(v)), full_median_same_pairs=float(np.median(f)),
         max_abs_diff=float(np.max(np.abs(v-f))),
         random_sub_gate_rate=float((v>0.05).mean()),
         full_gate_rate_at_M2=990/990)
print(json.dumps(out,indent=1,sort_keys=True))
json.dump(out,open(OUT/"t1_random_check.json","w"),indent=1,sort_keys=True)
