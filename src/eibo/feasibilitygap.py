"""Past-only retention deficits under unchanged APP21 and raw-error budgets."""

from __future__ import annotations

import numpy as np

from .costfrontier import pareto_mask

APPS = (22, 15)
DOMAINS = ("original_budget", "root_no_harm")
PROFILES = ("maximum_gain", "minimum_joint_rate", "minimum_joint_count",
    "minimum_APP22_rate", "minimum_APP15_rate", "relax_APP22_keep_APP15",
    "relax_APP15_keep_APP22", "identity", "stage17_all_keep_gains", "source_latest_family")


def gap_metrics(deltas, ns, priors, known, reference_index):
    """Positive deficits are class NET-error counts, never identified flows."""
    d, ns = np.asarray(deltas), np.asarray(ns)
    if d.ndim != 3 or ns.shape != (d.shape[0], d.shape[2]) or np.any(ns <= 0):
        raise ValueError("complete historical class denominators required")
    ix = [list(known).index(app) for app in APPS]
    changes = np.concatenate((d, d.sum(axis=0, keepdims=True)))
    denominators = np.concatenate((ns, ns.sum(axis=0, keepdims=True)))
    ref = changes[:, reference_index, :][:, ix]
    limits = np.minimum(0, ref)
    candidate = changes[:, :, ix]
    gaps = np.maximum(0, candidate - limits[:, None, :])
    foregone = np.minimum(gaps, -limits[:, None, :])
    harm = np.maximum(0, candidate)
    if not np.array_equal(gaps, foregone + harm):
        raise RuntimeError("retention gap does not conserve foregone gains plus new harm")
    rates = gaps / denominators[:, None, ix]
    gain = -((changes[-1] / denominators[-1]) @ np.asarray(priors))
    return {"changes": changes, "ns": denominators, "reference": ref, "limits": limits,
        "gaps": gaps, "foregone": foregone, "new_harm": harm, "rates": rates,
        "worst_rate": rates.max(axis=0), "worst_count": gaps.max(axis=0), "gain": gain}


def profile_indices(metrics, domain, candidate_ids, old_index, reference_index):
    """Fixed diagnostic objectives. This returns no new deployed rules."""
    gain, rates, counts = metrics["gain"], metrics["worst_rate"], metrics["worst_count"]
    positive = np.asarray(domain) & (gain > 1e-12)
    ids = np.asarray(candidate_ids)

    def best(value, mask=positive):
        indices = np.flatnonzero(mask)
        if not len(indices):
            return None
        # Exact gap ordering; ties: highest past gain, then smallest old ID.
        order = np.lexsort((ids[indices], -gain[indices], value[indices]))
        return int(indices[order[0]])

    return {"maximum_gain": best(-gain), "minimum_joint_rate": best(rates.max(axis=1)),
        "minimum_joint_count": best(counts.max(axis=1)),
        "minimum_APP22_rate": best(rates[:, 0]), "minimum_APP15_rate": best(rates[:, 1]),
        "relax_APP22_keep_APP15": best(rates[:, 0], positive & (counts[:, 1] == 0)),
        "relax_APP15_keep_APP22": best(rates[:, 1], positive & (counts[:, 0] == 0)),
        "identity": 0, "stage17_all_keep_gains": old_index, "source_latest_family": reference_index}


def diagnose(index, arrays, frozen, *, small_n=200):
    """Only stage-17 PAST arrays and old frozen choices enter this interface."""
    known, priors = index["known_service_codes"], index["known_priors"]
    choices = {(r["target"], r["model"]): r for r in frozen if r["group"] == "all_keep_gains"}
    summaries, profiles, bindings, coverage, frontiers, saved, points_index = [], [], [], [], [], {}, []
    for c in index["contexts"]:
        common = {k: c[k] for k in ("target", "period", "model")}
        if not c["available_current"]:
            summaries.extend({**common, "domain": domain, "status": "unavailable_current_fit"} for domain in DOMAINS)
            continue
        prefix = c["prefix"]
        d, ns, available = (arrays[prefix + "_" + name] for name in ("deltas", "ns", "history_available"))
        for h, origin in enumerate(c["history_node_ids"]):
            for j, app in enumerate(known):
                coverage.append({**common, "origin": origin, "APP": app, "prior": priors[j], "n": int(ns[h, j]),
                    "available": bool(available[h]), "small_n": bool(available[h] and 0 < ns[h, j] < small_n),
                    "one_net_count_pp": float(100 / ns[h, j]) if available[h] and ns[h, j] else None})
        if not available.all() or np.any(ns == 0):
            summaries.extend({**common, "domain": domain, "status": "incomplete_history"} for domain in DOMAINS)
            continue
        ref = c["candidate_ids"].index(c["reference_source_latest_candidate"]) if c["reference_source_latest_candidate"] is not None else 0
        old = choices[c["target"], c["model"]]
        old_i = c["candidate_ids"].index(old["rule"]["candidate_id"]) if old["rule"] else 0
        m = gap_metrics(d, ns, priors, known, ref)
        domains = {domain: arrays[prefix + "_all_" + field] for domain, field in
            (("original_budget", "original"), ("root_no_harm", "no_harm"))}
        for name in ("gaps", "foregone", "new_harm", "worst_rate", "worst_count", "gain"):
            saved[prefix + "_" + name] = m[name]
        points_index.append({**c, "reference_index": ref, "stage17_index": old_i})
        for domain, mask in domains.items():
            positive = mask & (m["gain"] > 1e-12)
            exact = mask & np.all(m["worst_count"] == 0, axis=1)
            if int(exact.sum()) != old["past_feasible_count"] or int((exact & positive).sum()) != old["past_positive_feasible_count"]:
                raise RuntimeError("gap-zero feasible set differs from stage 17")
            chosen = profile_indices(m, mask, c["candidate_ids"], old_i, ref)
            point_rows = {}
            front_counts = {}
            for unit, gaps in (("rate", m["worst_rate"]), ("count", m["worst_count"])):
                points = np.column_stack((-m["gain"], gaps))
                frontier = np.zeros(len(mask), dtype=bool)
                ids = np.flatnonzero(mask)
                frontier[ids] = pareto_mask(points[ids])
                saved[prefix + "_" + domain + "_" + unit + "_frontier"] = frontier
                front_counts[unit] = int(frontier.sum())
                # Keep all equivalent members in compact CSV rows. Equality
                # here refers to displayed costs, not fitted labels/predictions.
                for i in np.flatnonzero(frontier):
                    key = (unit, float(m["gain"][i]), *map(float, m["worst_rate"][i]), *map(int, m["worst_count"][i]))
                    point_rows.setdefault(key, []).append(int(c["candidate_ids"][i]))
            for key, ids in point_rows.items():
                frontiers.append({**common, "domain": domain, "frontier_units": key[0], "gain": key[1],
                    "APP22_rate_gap": key[2], "APP15_rate_gap": key[3], "APP22_count_gap": key[4], "APP15_count_gap": key[5],
                    "equivalent_rule_count": len(ids), "candidate_ids": ",".join(map(str, ids))})
            row = {**common, "domain": domain, "status": "ready", "candidates": int(mask.sum()), "positive_candidates": int(positive.sum()),
                "exact_candidates": int(exact.sum()), "exact_positive_candidates": int((exact & positive).sum()),
                "identity_qualified": bool(mask[0]), "identity_exact": bool(exact[0]),
                "positive_APP22_exact": int(np.sum(positive & (m["worst_count"][:, 0] == 0))),
                "positive_APP15_exact": int(np.sum(positive & (m["worst_count"][:, 1] == 0))),
                "rate_frontier_members": front_counts["rate"], "count_frontier_members": front_counts["count"]}
            for name, i in chosen.items():
                p = {**common, "domain": domain, "profile": name, "status": "diagnostic_point" if i is not None else "no_positive_qualified_candidate",
                    "candidate_id": c["candidate_ids"][i] if i is not None else None}
                if i is None:
                    profiles.append(p)
                    continue
                p.update(qualified=bool(mask[i]), positive_gain=bool(m["gain"][i] > 1e-12), gain=float(m["gain"][i]),
                    worst_joint_rate_gap=float(m["worst_rate"][i].max()), worst_joint_count_gap=int(m["worst_count"][i].max()),
                    exact_retention=bool(np.all(m["worst_count"][i] == 0)))
                for j, app in enumerate(APPS):
                    p.update({f"APP{app}_worst_rate_gap": float(m["worst_rate"][i, j]),
                        f"APP{app}_worst_count_gap": int(m["worst_count"][i, j]),
                        f"APP{app}_monthly_gap_sum": int(m["gaps"][:-1, i, j].sum()),
                        f"APP{app}_pooled_gap": int(m["gaps"][-1, i, j])})
                    for h, origin in enumerate(c["history_node_ids"] + ["pooled"]):
                        n, gap, rate = int(m["ns"][h, known.index(app)]), int(m["gaps"][h, i, j]), float(m["rates"][h, i, j])
                        bindings.append({**common, "domain": domain, "profile": name, "candidate_id": c["candidate_ids"][i],
                            "origin": origin, "pooled": origin == "pooled", "APP": app, "n": n, "prior": priors[known.index(app)],
                            "reference_delta": int(m["reference"][h, j]), "retention_limit": int(m["limits"][h, j]),
                            "candidate_delta": int(m["changes"][h, i, known.index(app)]), "gap": gap,
                            "net_gain_foregone": int(m["foregone"][h, i, j]), "new_root_harm": int(m["new_harm"][h, i, j]),
                            "rate_gap": rate, "weighted_gap": float(priors[known.index(app)] * rate),
                            "one_net_count_pp": 100 / n, "small_n": n < small_n,
                            "class_rate_binding": bool(gap > 0 and rate == m["worst_rate"][i, j]),
                            "joint_rate_binding": bool(gap > 0 and rate == m["worst_rate"][i].max()),
                            "class_count_binding": bool(gap > 0 and gap == m["worst_count"][i, j])})
                profiles.append(p)
            for label, name, metric in (("joint_rate_gap", "minimum_joint_rate", "worst_rate"),
                ("joint_count_gap", "minimum_joint_count", "worst_count")):
                i = chosen[name]
                row[label] = float(m[metric][i].max()) if i is not None else None
            summaries.append(row)
    return {"summaries": summaries, "profiles": profiles, "bindings": bindings, "coverage": coverage,
            "frontiers": frontiers, "arrays": saved, "index": points_index}
