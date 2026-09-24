"""T1: classifier-based lower side at M > 1, on the SYMBOL-MAP object.

Object under test (settled 2026-09-19, see M163): the one-hot projection of the
packed k-prefix SYMBOL law over the a-priori-fixed categorical alphabet (2M)^k,
NOT the four-marginal-histogram 32-vector object in
compute_vector_level_one_sided_full_n.py. The published M=1 lower side
(q1_eps_lo_symbol_map.json, alphabet_cardinality_m=32, median eps_lo 0.534945)
is this object; the vector-level file self-reports "not used as a lower bound on
the marginal k-prefix symbol-law TV".

Alphabet width: 32 (M=1,k=5), 1024 (M=2,k=5), 32768 (M=4,k=5). Sparse, never densified.

Phase A (control): rebuild the M=1 rung and assert it reproduces the published
counts before any M>=2 work runs.
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import tables

ROOT = Path(__file__).resolve().parents[1]
H5 = os.environ.get("EIBO_H5", "/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5")
OUT_DIR = ROOT / "artifacts" / "_project" / "intermediate"
DIRECTION_ROW, SIZE_ROW = 1, 2
K = 5
BATCH = 100_000

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


def rung_counts(packer, m: int, max_tables: int | None = None) -> dict[int, dict[int, int]]:
    """Per-service histogram of packed k-prefix symbols at rung M=m."""
    counts: dict[int, dict[int, int]] = {}
    t0 = time.time()
    ntab = 0
    with tables.open_file(H5, mode="r") as h5:
        for node in h5.walk_nodes("/flows", classname="Table"):
            if "APP" not in node.colnames:
                continue
            ntab += 1
            if max_tables is not None and ntab > max_tables:
                break
            n = node.nrows
            for start in range(0, n, BATCH):
                stop = min(start + BATCH, n)
                app = np.asarray(node.read(start=start, stop=stop, field="APP"), dtype=np.int16)
                ppi = np.asarray(node.read(start=start, stop=stop, field="PPI"))
                lens = np.asarray(node.read(start=start, stop=stop, field="PPI_LEN"))
                ok = lens >= K
                if not ok.any():
                    continue
                app, ppi = app[ok], ppi[ok]
                codes = packer.pack_rung_prefix(ppi, K, m, DIRECTION_ROW, SIZE_ROW)
                for a, c in zip(app.tolist(), codes):
                    d = counts.setdefault(int(a), {})
                    d[c] = d.get(c, 0) + 1
            if ntab % 50 == 0:
                print(
                    "  tables=%d elapsed=%.0fs services=%d"
                    % (ntab, time.time() - t0, len(counts)),
                    flush=True,
                )
    print(
        "  DONE tables=%d elapsed=%.0fs services=%d"
        % (ntab, time.time() - t0, len(counts)),
        flush=True,
    )
    return counts


def assert_existing_execution_environment_preserved(path: Path, payload: dict) -> None:
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


def save(obj, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / name
    payload = dict(obj)
    if p.exists():
        with open(p, encoding="utf-8") as fh:
            existing = json.load(fh)
        if "execution_environment" in existing:
            payload = {"execution_environment": existing["execution_environment"], **payload}
    assert_existing_execution_environment_preserved(p, payload)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    print("wrote %s" % p, flush=True)
    return p


def main() -> int:
    packer = load_packer()
    print("=== T1 phase A: M=1 control rung ===", flush=True)
    t0 = time.time()
    c1 = rung_counts(packer, m=1)
    elapsed = time.time() - t0
    total = sum(sum(d.values()) for d in c1.values())
    payload = {
        "rung_M": 1,
        "k": K,
        "alphabet_cardinality": (2 * 1) ** K,
        "services": len(c1),
        "total_masked_flows": total,
        "elapsed_seconds": round(elapsed, 1),
        "object": "packed k-prefix SYMBOL law over (2M)^k, one-hot, symbol-map construction",
        "counts": {str(s): {str(c): n for c, n in d.items()} for s, d in c1.items()},
    }
    save(payload, "t1_m1_rung_counts.json")
    print("services=%d total_flows=%d elapsed=%.0fs" % (len(c1), total, elapsed), flush=True)
    return 0


def gate_services(counts_by_rung, min_flows=2000):
    """Services passing the >=2000 masked-flow threshold, applied consistently across rungs."""
    keep = None
    for counts in counts_by_rung:
        s = {k for k, d in counts.items() if sum(d.values()) >= min_flows}
        keep = s if keep is None else (keep & s)
    return sorted(keep)


SAMPLE_CAP_PER_SERVICE = 20000
SAMPLE_SEED = 20260913


def onehot_sampled(counts, svc, m, rng):
    """One-hot rows for one service, capped at published sample_cap_per_service.

    The M=1 protocol (q1_eps_lo_symbol_map.json metadata.lower_side) caps at
    20000 flows per service with sample_seed 20260913. tv_lower_bound densifies
    internally (np.asarray(X1, dtype=float)), so the width is a hard memory
    constraint: at M=4 a single uncapped service would need ~367 GB per matrix.
    """
    width = (2 * m) ** K
    syms = []
    for sym, n in counts[svc].items():
        syms.extend([int(sym)] * int(n))
    syms = np.asarray(syms, dtype=np.int64)
    if len(syms) > SAMPLE_CAP_PER_SERVICE:
        syms = rng.choice(syms, size=SAMPLE_CAP_PER_SERVICE, replace=False)
    return syms, width


def main_full() -> int:
    from eibo.statcore import tv_lower_bound
    import itertools
    import sklearn

    packer = load_packer()
    rungs = [1, 2, 4]
    counts_by_rung = []
    for m in rungs:
        cache = OUT_DIR / ("t1_m%d_rung_counts.json" % m)
        if cache.exists():
            print("=== reusing cached rung M=%d ===" % m, flush=True)
            counts_by_rung.append(
                {int(s): {int(c2): n for c2, n in d.items()}
                 for s, d in json.load(open(cache))["counts"].items()}
            )
            continue
        print("=== building rung M=%d (alphabet %d) ===" % (m, (2 * m) ** K), flush=True)
        t0 = time.time()
        c = rung_counts(packer, m=m)
        print("  M=%d done in %.0fs, services=%d, flows=%d"
              % (m, time.time() - t0, len(c), sum(sum(d.values()) for d in c.values())), flush=True)
        counts_by_rung.append(c)
        save({"rung_M": m, "k": K, "alphabet_cardinality": (2 * m) ** K,
              "services": len(c), "total_masked_flows": sum(sum(d.values()) for d in c.values()),
              "counts": {str(s): {str(c2): n for c2, n in d.items()} for s, d in c.items()}},
             "t1_m%d_rung_counts.json" % m)

    svcs = gate_services(counts_by_rung)
    print("gate services (>=2000 masked flows at every rung): %d" % len(svcs), flush=True)
    print("sklearn present: %s" % sklearn.__version__, flush=True)
    print("sample cap per service: %d, seed %d" % (SAMPLE_CAP_PER_SERVICE, SAMPLE_SEED), flush=True)

    results = {}
    for m, c in zip(rungs, counts_by_rung):
        rng = np.random.default_rng(SAMPLE_SEED)
        idx_by_svc = {s: onehot_sampled(c, s, m, rng) for s in svcs}
        width = (2 * m) ** K
        print("M=%d: width=%d, sampled flows/service<=%d, starting classifier phase"
              % (m, width, SAMPLE_CAP_PER_SERVICE), flush=True)
        rows = []
        for i, (a, b) in enumerate(itertools.combinations(svcs, 2)):
            ia, _ = idx_by_svc[a]
            ib, _ = idx_by_svc[b]
            Xa = np.zeros((len(ia), width), dtype=np.float32); Xa[np.arange(len(ia)), ia] = 1.0
            Xb = np.zeros((len(ib), width), dtype=np.float32); Xb[np.arange(len(ib)), ib] = 1.0
            lo, diag = tv_lower_bound(Xa, Xb, alpha=0.025, random_state=0, method="michel")
            rows.append({"service_a": a, "service_b": b, "n_a": int(len(ia)), "n_b": int(len(ib)),
                         "eps_lo": float(lo),
                         "raw": float(diag.get("raw_statistic", float("nan")))})
            if (i + 1) % 50 == 0:
                print("  M=%d pairs=%d/%d" % (m, i + 1, len(svcs) * (len(svcs) - 1) // 2), flush=True)
        pair_vals = np.array([r["eps_lo"] for r in rows])
        summary = {"rung_M": m, "alphabet_cardinality": width, "pairs": len(rows),
                   "sample_cap_per_service": SAMPLE_CAP_PER_SERVICE,
                   "eps_lo_median": float(np.median(pair_vals)),
                   "eps_lo_q5": float(np.percentile(pair_vals, 5)),
                   "eps_lo_q95": float(np.percentile(pair_vals, 95)),
                   "lower_side_pairs_gt_0.05": int((pair_vals > 0.05).sum())}
        results["M=%d" % m] = {"summary": summary, "rows": rows,
                                "provenance": execution_environment_provenance()}
        print("M=%d summary: %s" % (m, json.dumps(summary)), flush=True)
        save(results["M=%d" % m], "t1_lower_side_M%d.json" % m)
    save(results, "t1_lower_side_all_rungs.json")
    return 0


if __name__ == "__main__":
    import sys as _sys
    raise SystemExit(main_full() if "--full" in _sys.argv else main())
