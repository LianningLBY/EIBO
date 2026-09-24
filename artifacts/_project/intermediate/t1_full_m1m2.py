"""T1 full run: M in {1,2} only. M=4 projected at 7.5-42h and is deferred pending a decision."""
import importlib.util, json, sys, time, itertools
from pathlib import Path
import numpy as np
ROOT=Path("/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade")
sys.path.insert(0,str(ROOT/"src"))
OUT=ROOT/"artifacts/_project/intermediate"
spec=importlib.util.spec_from_file_location("t1",ROOT/"scripts/t1_lower_side_at_M.py")
t1=importlib.util.module_from_spec(spec); spec.loader.exec_module(t1)
from eibo.statcore import tv_lower_bound

RUNGS=[1,2]
counts={m:{int(s):{int(k):v for k,v in d.items()} for s,d in json.load(open(OUT/("t1_m%d_rung_counts.json"%m)))["counts"].items()} for m in RUNGS}
svcs=t1.gate_services([counts[m] for m in RUNGS])
allpairs=list(itertools.combinations(svcs,2))
print("rungs=%s gated_services=%d pairs=%d"%(RUNGS,len(svcs),len(allpairs)),flush=True)

for m in RUNGS:
    rng=np.random.default_rng(t1.SAMPLE_SEED)
    idx={s: t1.onehot_sampled(counts[m],s,m,rng) for s in svcs}
    width=(2*m)**t1.K
    rows=[]; t0=time.time()
    print("M=%d width=%d starting"%(m,width),flush=True)
    for i,(a,b) in enumerate(allpairs):
        ia,_=idx[a]; ib,_=idx[b]
        Xa=np.zeros((len(ia),width),dtype=np.float32); Xa[np.arange(len(ia)),ia]=1.0
        Xb=np.zeros((len(ib),width),dtype=np.float32); Xb[np.arange(len(ib)),ib]=1.0
        lo,diag=tv_lower_bound(Xa,Xb,alpha=0.025,random_state=0,method="michel")
        rows.append(dict(service_a=a,service_b=b,n_a=int(len(ia)),n_b=int(len(ib)),
                         eps_lo=float(lo),tv_hat=float(diag.get("raw_statistic",float("nan")))))
        if (i+1)%100==0:
            el=time.time()-t0
            print("  M=%d %d/%d elapsed=%.0fs rate=%.2fs/pair eta=%.0fmin"%(
                m,i+1,len(allpairs),el,el/(i+1),el/(i+1)*(len(allpairs)-i-1)/60),flush=True)
    v=np.array([r["eps_lo"] for r in rows])
    summary=dict(rung_M=m,alphabet_cardinality=width,pairs=len(rows),
                 sample_cap_per_service=t1.SAMPLE_CAP_PER_SERVICE,
                 eps_lo_median=float(np.median(v)),eps_lo_q5=float(np.percentile(v,5)),
                 eps_lo_q95=float(np.percentile(v,95)),
                 lower_side_pairs_gt_0point05=int((v>0.05).sum()),
                 seconds=round(time.time()-t0,1))
    print("M=%d summary %s"%(m,json.dumps(summary)),flush=True)
    json.dump(dict(summary=summary,rows=rows),open(OUT/("t1_lower_side_M%d.json"%m),"w"),indent=1,sort_keys=True)
    print("  wrote t1_lower_side_M%d.json"%m,flush=True)
