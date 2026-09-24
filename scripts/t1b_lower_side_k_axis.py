"""T1b: the k-companion to T1. Does the classifier lower side stop binding as k refines,
the way it does as M refines?

T1 established, on the M axis at k=5 fixed:
  M=1 (width 32)   : lower median eps_lo 0.53677, 986/990 clear the 0.05 gate, joint 359
  M=2 (width 1024) : lower median eps_lo 0.85352, 990/990 clear the gate,     joint 127
with the joint gate at M=2 set entirely by the upper bound.

This runs the SAME object (one-hot over the packed k-prefix symbol law) along the OTHER axis:
k in {5, 10} at M=1 fixed. Width is (2M)^k = 2^k, so k=10 gives 1024 — the same feature width
as T1's M=2 cell, which is the comparison that makes the two axes comparable.

Protocol is identical to T1 (sample cap 20000/service, seed 20260913, alpha 0.025,
random_state 0, method michel, sklearn LogisticRegression) so the columns are like-for-like.
"""
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import tables

ROOT = Path(__file__).resolve().parents[1]
H5 = os.environ.get("EIBO_H5", "/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5")
OUT = ROOT / "artifacts" / "_project" / "intermediate"
DIRECTION_ROW, SIZE_ROW = 1, 2
M_FIXED = 1
BATCH = 100_000
SAMPLE_CAP, SAMPLE_SEED = 20000, 20260913
ALPHA = 0.025
H0 = 2 * math.log(2 / ALPHA)

sys.path.insert(0, str(ROOT / "src"))


def load_packer():
    spec = importlib.util.spec_from_file_location(
        "xscr", ROOT / "scripts" / "xs_compression_early_readout.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def execution_environment_provenance():
    import os
    import platform
    import sys
    try:
        import sklearn
        from sklearn.linear_model import LogisticRegression
        probe = LogisticRegression(max_iter=1000, random_state=0).fit(
            [[0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], [0, 1, 0, 1])
        solver = getattr(probe, "solver", None)
        penalty = getattr(probe, "penalty", None)
        version = sklearn.__version__
    except Exception as exc:
        solver = penalty = version = None
        print("provenance probe failed: %r" % (exc,), flush=True)
    try:
        host = platform.node()
    except Exception:
        host = None
    try:
        cwd = os.getcwd()
    except Exception:
        cwd = None
    return {
        "sklearn": version,
        "resolved_solver": solver,
        "resolved_penalty": penalty,
        "python_version": sys.version.split()[0],
        "python_path": sys.executable,
        "host": host,
        "cwd": cwd,
    }


def assert_existing_execution_environment_preserved(path, payload):
    if not path.exists():
        return
    with open(path, encoding="utf-8") as fh:
        existing_env = json.load(fh).get("execution_environment", {})
    candidate_env = payload.get("execution_environment", {})
    lost = sorted(set(existing_env) - set(candidate_env))
    if lost:
        raise RuntimeError(
            "refusing to overwrite %s: execution_environment keys would be lost: %s"
            % (path, ", ".join(lost))
        )


def write_json(path, obj):
    payload = dict(obj)
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            existing = json.load(fh)
        if "execution_environment" in existing:
            payload = {"execution_environment": existing["execution_environment"], **payload}
    assert_existing_execution_environment_preserved(path, payload)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)


def rung_counts(packer, k: int, m: int):
    """Per-service histogram of packed k-prefix symbols at (k, m)."""
    counts: dict[int, dict[int, int]] = {}
    t0, ntab = time.time(), 0
    with tables.open_file(H5, mode="r") as h5:
        for node in h5.walk_nodes("/flows", classname="Table"):
            if "APP" not in node.colnames:
                continue
            ntab += 1
            n = node.nrows
            for start in range(0, n, BATCH):
                stop = min(start + BATCH, n)
                app = np.asarray(node.read(start=start, stop=stop, field="APP"), dtype=np.int16)
                ppi = np.asarray(node.read(start=start, stop=stop, field="PPI"))
                lens = np.asarray(node.read(start=start, stop=stop, field="PPI_LEN"))
                ok = lens >= k
                if not ok.any():
                    continue
                app, ppi = app[ok], ppi[ok]
                codes = packer.pack_rung_prefix(ppi, k, m, DIRECTION_ROW, SIZE_ROW)
                for a, c in zip(app.tolist(), codes):
                    d = counts.setdefault(int(a), {})
                    d[c] = d.get(c, 0) + 1
            if ntab % 50 == 0:
                print("  k=%d tables=%d elapsed=%.0fs services=%d"
                      % (k, ntab, time.time() - t0, len(counts)), flush=True)
    print("  k=%d DONE tables=%d elapsed=%.0fs services=%d"
          % (k, ntab, time.time() - t0, len(counts)), flush=True)
    return counts


def sampled_onehot(counts, svc, width, rng):
    syms = []
    for sym, n in counts[svc].items():
        syms.extend([int(sym)] * int(n))
    syms = np.asarray(syms, dtype=np.int64)
    if len(syms) > SAMPLE_CAP:
        syms = rng.choice(syms, size=SAMPLE_CAP, replace=False)
    return syms


def main() -> int:
    import itertools
    from eibo.statcore import tv_lower_bound
    import sklearn

    packer = load_packer()
    ks = [5, 10]
    print("sklearn %s | M fixed at %d | k in %s" % (sklearn.__version__, M_FIXED, ks), flush=True)

    per_k = {}
    for k in ks:
        cache = OUT / ("t1b_k%d_m%d_counts.json" % (k, M_FIXED))
        if cache.exists():
            print("=== reusing cached counts k=%d ===" % k, flush=True)
            d = json.load(open(cache))
            per_k[k] = {int(s): {int(c): v for c, v in dd.items()} for s, dd in d["counts"].items()}
            continue
        print("=== building counts for k=%d (alphabet %d) ===" % (k, 2 ** k), flush=True)
        c = rung_counts(packer, k, M_FIXED)
        per_k[k] = c
        write_json(cache, {"k": k, "M": M_FIXED, "alphabet_cardinality": 2 ** k,
                           "services": len(c), "total_masked_flows": sum(sum(v.values()) for v in c.values()),
                           "counts": {str(s): {str(cc): v for cc, v in dd.items()} for s, dd in c.items()}})
        print("  wrote %s" % cache, flush=True)

    # gate services consistently across both k (>=2000 masked flows at every k)
    keep = None
    for k in ks:
        s = {svc for svc, d in per_k[k].items() if sum(d.values()) >= 2000}
        keep = s if keep is None else (keep & s)
    svcs = sorted(keep)
    print("gated services: %d" % len(svcs), flush=True)

    # upper side (m-free) at (k, M=1) from the published per-pair ledgers
    def upper_map(k):
        f = OUT.parent / "data" / ("q1_absolute_counts.json" if k == 5 else "q1_absolute_counts_k%d.json" % k)
        key = "tv_k%d_masked" % k
        out = {}
        for r in json.load(open(f))["pairs"]:
            if r["M"] != M_FIXED:
                continue
            tv, na, nb = r[key], r["n_a"], r["n_b"]
            out[(int(r["service_a"]), int(r["service_b"]))] = min(
                1.0, tv + 0.5 * math.sqrt(H0 / na) + 0.5 * math.sqrt(H0 / nb))
        return out

    result = {}
    for k in ks:
        width = 2 ** k
        rng = np.random.default_rng(SAMPLE_SEED)
        idx = {s: sampled_onehot(per_k[k], s, width, rng) for s in svcs}
        up = upper_map(k)
        rows = []
        t0 = time.time()
        print("k=%d width=%d starting classifier phase" % (k, width), flush=True)
        for i, (a, b) in enumerate(itertools.combinations(svcs, 2)):
            ia, ib = idx[a], idx[b]
            Xa = np.zeros((len(ia), width), dtype=np.float32); Xa[np.arange(len(ia)), ia] = 1.0
            Xb = np.zeros((len(ib), width), dtype=np.float32); Xb[np.arange(len(ib)), ib] = 1.0
            lo, diag = tv_lower_bound(Xa, Xb, alpha=ALPHA, random_state=0, method="michel")
            ehi = up.get((a, b))
            rows.append(dict(service_a=a, service_b=b, n_a=int(len(ia)), n_b=int(len(ib)),
                             eps_lo=float(lo), eps_hi_upper_mfree=ehi,
                             tv_hat=float(diag.get("raw_statistic", float("nan")))))
            if (i + 1) % 100 == 0:
                el = time.time() - t0
                print("  k=%d %d/%d elapsed=%.0fs rate=%.2fs/pair" % (k, i + 1, len(rows), el, el / (i + 1)),
                      flush=True)
        v = np.array([r["eps_lo"] for r in rows])
        viol = [r for r in rows if r["eps_hi_upper_mfree"] is not None
                and r["eps_lo"] > r["eps_hi_upper_mfree"] + 1e-12]
        joint = sum(1 for r in rows if r["eps_lo"] > 0.05
                    and r["eps_hi_upper_mfree"] is not None and r["eps_hi_upper_mfree"] < 0.5)
        upper_only = sum(1 for r in rows if r["eps_hi_upper_mfree"] is not None
                         and r["eps_hi_upper_mfree"] < 0.5)
        summary = dict(k=k, M=M_FIXED, alphabet_cardinality=width, pairs=len(rows),
                       sample_cap_per_service=SAMPLE_CAP,
                       eps_lo_median=float(np.median(v)),
                       eps_lo_q5=float(np.percentile(v, 5)),
                       eps_lo_q95=float(np.percentile(v, 95)),
                       lower_side_pairs_gt_0point05=int((v > 0.05).sum()),
                       upper_only_lt_0point5=upper_only,
                       joint_gate=joint,
                       invariant_checked="eps_lo <= eps_hi (m-free upper, per pair, same pair set)",
                       invariant_violations=len(viol),
                       seconds=round(time.time() - t0, 1))
        result["k=%d" % k] = {"summary": summary, "rows": rows,
                               "provenance": execution_environment_provenance()}
        print("k=%d summary %s" % (k, json.dumps(summary)), flush=True)
        write_json(OUT / ("t1b_lower_side_k%d.json" % k), result["k=%d" % k])
    write_json(OUT / "t1b_lower_side_k_axis.json", result)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
