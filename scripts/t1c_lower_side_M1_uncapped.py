"""T1c: the UNCAPPED M=1 lower side, from the stored histogram.

Why this matters: T1/T1b used the capped convention (20000 flows/service). The published
ledger has both conventions and they differ by exactly one joint-gate pair (21,23). Whether
that difference propagates to T1's conclusion has been an open caveat. The M=1 cell at
width 32 needs only ~0.72 GB uncapped (n_max 1,399,495), so it fits locally even though
width 1024 does not (~22.9 GB against a measured ~16 GB ceiling).

The stored rung histogram (t1_m1_rung_counts.json) is UNCAPPED — full per-service counts —
so this needs no corpus read.

Protocol otherwise identical to T1: alpha 0.025, random_state 0, method michel, sklearn.
"""
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "_project" / "intermediate"
DIRECTION_ROW, SIZE_ROW, K, M_FIXED = 1, 2, 5, 1
ALPHA = 0.025
H0 = 2 * math.log(2 / ALPHA)

sys.path.insert(0, str(ROOT / "src"))


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


def main() -> int:
    import itertools
    from eibo.statcore import tv_lower_bound

    spec = importlib.util.spec_from_file_location("t1", ROOT / "scripts" / "t1_lower_side_at_M.py")
    t1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t1)

    d = json.load(open(OUT / "t1_m1_rung_counts.json"))
    counts = {int(s): {int(c): v for c, v in dd.items()} for s, dd in d["counts"].items()}
    print("services in histogram: %d, total flows %d" % (len(counts), sum(sum(v.values()) for v in counts.values())),
          flush=True)

    svcs = t1.gate_services([counts])
    print("gated services: %d" % len(svcs), flush=True)

    # uncapped one-hot: every flow, no subsample
    width = 2 ** K
    idx = {}
    for s in svcs:
        syms = []
        for sym, n in counts[s].items():
            syms.extend([int(sym)] * int(n))
        idx[s] = np.asarray(syms, dtype=np.int64)
    print("uncapped rows/service: min %d max %d (width %d)"
          % (min(len(v) for v in idx.values()), max(len(v) for v in idx.values()), width), flush=True)

    # upper side (m-free) at M=1, k=5, from the published per-pair ledger (full-n counts)
    up = {}
    for r in json.load(open(OUT.parent / "data" / "q1_absolute_counts.json"))["pairs"]:
        if r["M"] != M_FIXED:
            continue
        na, nb = r["n_a"], r["n_b"]
        up[(int(r["service_a"]), int(r["service_b"]))] = min(
            1.0, r["tv_k5_masked"] + 0.5 * math.sqrt(H0 / na) + 0.5 * math.sqrt(H0 / nb))

    rows = []
    t0 = time.time()
    pairs = list(itertools.combinations(svcs, 2))
    print("pairs: %d, starting" % len(pairs), flush=True)
    for i, (a, b) in enumerate(pairs):
        ia, ib = idx[a], idx[b]
        Xa = np.zeros((len(ia), width), dtype=np.float32); Xa[np.arange(len(ia)), ia] = 1.0
        Xb = np.zeros((len(ib), width), dtype=np.float32); Xb[np.arange(len(ib)), ib] = 1.0
        lo, diag = tv_lower_bound(Xa, Xb, alpha=ALPHA, random_state=0, method="michel")
        rows.append(dict(service_a=a, service_b=b, n_a=int(len(ia)), n_b=int(len(ib)),
                         eps_lo=float(lo), eps_hi_upper_mfree=up.get((a, b)),
                         tv_hat=float(diag.get("raw_statistic", float("nan")))))
        if (i + 1) % 100 == 0:
            el = time.time() - t0
            print("  %d/%d elapsed=%.0fs rate=%.2fs/pair" % (i + 1, len(pairs), el, el / (i + 1)), flush=True)

    v = np.array([r["eps_lo"] for r in rows])
    viol = [r for r in rows if r["eps_hi_upper_mfree"] is not None
            and r["eps_lo"] > r["eps_hi_upper_mfree"] + 1e-12]
    joint = sum(1 for r in rows if r["eps_lo"] > 0.05
                and r["eps_hi_upper_mfree"] is not None and r["eps_hi_upper_mfree"] < 0.5)
    upper_only = sum(1 for r in rows if r["eps_hi_upper_mfree"] is not None
                     and r["eps_hi_upper_mfree"] < 0.5)
    summary = dict(
        convention="UNCAPPED (full per-service flow counts)",
        k=K, M=M_FIXED, alphabet_cardinality=width, pairs=len(rows),
        sample_cap_per_service=None,
        eps_lo_median=float(np.median(v)),
        lower_side_pairs_gt_0point05=int((v > 0.05).sum()),
        upper_only_lt_0point5=upper_only,
        joint_gate=joint,
        invariant_checked="eps_lo <= eps_hi (m-free upper, per pair, same pair set)",
        invariant_violations=len(viol),
        seconds=round(time.time() - t0, 1),
    )
    print("summary %s" % json.dumps(summary), flush=True)
    write_json(OUT / "t1c_lower_side_M1_uncapped.json",
               {"summary": summary, "rows": rows,
                "provenance": execution_environment_provenance()})
    print("wrote t1c_lower_side_M1_uncapped.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
