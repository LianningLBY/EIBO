#!/usr/bin/env python3
import collections
import csv
import hashlib
import json
from pathlib import Path


BASE = Path("/root/eibo/artifacts")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    rows = json.loads((BASE / "q1_absolute_counts.json").read_text())["pairs"]
    keys = {"service_a", "service_b", "M", "n_a", "n_b", "tv_k5_masked"}
    assert len(rows) == 4950
    assert all(set(row) == keys for row in rows)
    assert all(int(row["service_a"]) < int(row["service_b"]) for row in rows)
    assert len({(r["service_a"], r["service_b"], r["M"]) for r in rows}) == 4950
    assert collections.Counter(r["M"] for r in rows) == collections.Counter(
        {1: 990, 2: 990, 4: 990, 8: 990, 16: 990}
    )

    csv_rows = list(csv.DictReader(open(BASE / "q1_absolute_counts.csv", newline="")))
    assert len(csv_rows) == 4950
    assert all(set(row) == keys for row in csv_rows)

    meta = json.loads((BASE / "q1_absolute_counts.meta.json").read_text())
    summary = json.loads((BASE / "q1_absolute_summary.json").read_text())
    assert meta["row_count"] == 4950
    assert meta["pairing"]["services_retained"] == 45
    assert meta["k5_denominator_exactness"]["post_mask_usable_pairs"] == 990
    assert len(summary["per_rung"]) == 5

    dense = json.loads((BASE / "q1_absolute_dense_counts_m1_m2.json").read_text())
    recomputed = 0
    max_error = 0.0
    for m in (1, 2):
        alphabet = dense[str(m)]["alphabet_cardinality"]
        counts = dense[str(m)]["counts_by_service"]
        assert all(len(vector) == alphabet for vector in counts.values())
        for row in rows:
            if row["M"] != m:
                continue
            a = counts[row["service_a"]]
            b = counts[row["service_b"]]
            n_a = sum(a)
            n_b = sum(b)
            assert n_a == int(row["n_a"]) and n_b == int(row["n_b"])
            tv = 0.5 * sum(
                abs(a[i] / n_a - b[i] / n_b) for i in range(alphabet)
            )
            max_error = max(max_error, abs(tv - float(row["tv_k5_masked"])))
            assert abs(tv - float(row["tv_k5_masked"])) < 1e-12
            recomputed += 1

    print(
        json.dumps(
            {
                "rows": len(rows),
                "csv_rows": len(csv_rows),
                "m_counts": dict(collections.Counter(r["M"] for r in rows)),
                "dense_tv_recomputed_rows": recomputed,
                "dense_tv_max_abs_error": max_error,
                "summary_rungs": len(summary["per_rung"]),
                "source_h5_sha256": meta["source_h5"]["sha256"],
                "artifact_sha256": {
                    name: digest(BASE / name)
                    for name in (
                        "q1_absolute_summary.json",
                        "q1_absolute_counts.json",
                        "q1_absolute_counts.csv",
                        "q1_absolute_counts.meta.json",
                    )
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
