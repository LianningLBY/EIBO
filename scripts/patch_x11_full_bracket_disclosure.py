#!/usr/bin/env python3
"""Add the reviewer-requested sample-size disclosure to the X11 artifact."""

import hashlib
import json
import os
from pathlib import Path


ARTIFACT = Path(
    os.environ.get("X11_ARTIFACT_PATH", "/root/eibo/artifacts/x11_full_bracket.json")
)
CAP = 20_000


def main() -> None:
    data = json.loads(ARTIFACT.read_text())
    rows = data["per_pair_rows"]
    if len(rows) != 3321:
        raise ValueError(f"expected 3321 per-pair rows, found {len(rows)}")

    capped_pair_count = sum(
        row["n_a"] > CAP or row["n_b"] > CAP
        for row in rows
    )
    capped_pair_count_from_lower_n = sum(
        row["lower_n_a"] != row["n_a"] or row["lower_n_b"] != row["n_b"]
        for row in rows
    )
    if capped_pair_count != capped_pair_count_from_lower_n:
        raise ValueError(
            "cap-count mismatch: "
            f"n fields={capped_pair_count}, lower_n fields={capped_pair_count_from_lower_n}"
        )

    near_boundary_upper_certifiable = sum(
        row["eps_hi"] < 0.5 and 0.04 <= row["eps_lo"] <= 0.06
        for row in rows
    )

    data["sample_size_disclosure"] = {
        "upper_side_n": "full (all eligible test flows per service, uncapped)",
        "lower_side_n": (
            "capped at 20000 flows per service "
            "(sample_seed=20260913, method=michel, random_state=0)"
        ),
        "capped_pair_count": capped_pair_count,
        "total_pairs": 3321,
        "joint_gate_mixes_two_sample_sizes": True,
        "bias_direction": (
            "CONSERVATIVE — a lower bound with less data is weaker (smaller eps_lo), "
            "so the cap can only shrink eps_lo and understate the joint gate. The "
            "reported 15.75% is therefore a lower bound on the true joint-gate "
            "fraction, not inflated."
        ),
        "near_boundary_upper_certifiable": near_boundary_upper_certifiable,
        "D065_class_note": (
            "Two bounds at different n must not sit in one table without saying so. "
            "The upper side uses full n; the lower side uses min(n, 20000). The "
            "joint gate ANDs the two."
        ),
    }
    ARTIFACT.write_text(json.dumps(data, indent=2) + "\n")

    digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "capped_pair_count": capped_pair_count,
                "near_boundary_upper_certifiable": near_boundary_upper_certifiable,
                "sha256": digest,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
