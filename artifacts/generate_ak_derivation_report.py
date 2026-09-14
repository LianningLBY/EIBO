import json
import math
from pathlib import Path

import numpy as np


ROOT = Path.cwd()
OUT = ROOT / "artifacts" / "ak_derivation_report.json"

ALPHA = 0.05
M_VALUES = [2, 3, 4, 5, 10]
N_VALUES = [10**3, 10**4, 10**5, 10**6, 10**7]
TV_VALUES = [0.1, 0.2, 0.3, 0.4]
K_VALUES = list(range(1, 31))
K_WINDOW = list(range(5, 16))
C_ALPHA = float(np.sqrt(2.0 * np.log(2.0 / ALPHA)))


def radius(m, n):
    return 0.5 * math.sqrt(m / n) + 0.5 * C_ALPHA / math.sqrt(n)


def k_cert(M, n, tv_hat):
    k = np.asarray(K_VALUES, dtype=float)
    m_grid = np.power(float(2 * M), k)
    total = float(tv_hat) + np.sqrt(m_grid / float(n)) + C_ALPHA / math.sqrt(float(n))
    passing = k[total < 0.5]
    return int(passing.max()) if passing.size else None


def k_table():
    rows = []
    for M in M_VALUES:
        for n in N_VALUES:
            rows.append(
                {
                    "M": M,
                    "n1_equals_n2": n,
                    "k_cert_by_tv_hat": {
                        str(tv): k_cert(M, n, tv) for tv in TV_VALUES
                    },
                }
            )
    return rows


def in_window_rows(table):
    rows = []
    for row in table:
        for tv in TV_VALUES:
            value = row["k_cert_by_tv_hat"][str(tv)]
            if value is not None and 5 <= value <= 15:
                rows.append(
                    {
                        "M": row["M"],
                        "n": row["n1_equals_n2"],
                        "tv_hat": tv,
                        "k_cert": value,
                    }
                )
    return rows


def m_max(k, n, tv_hat):
    budget = 0.5 - float(tv_hat) - C_ALPHA / math.sqrt(float(n))
    if budget <= 0.0:
        return 0
    threshold = 0.5 * (float(n) * budget * budget) ** (1.0 / float(k))
    # The strict certificate condition is M < threshold, so the largest
    # integer M is ceil(threshold)-1.  Direct verification handles rounding.
    candidate = max(0, int(math.ceil(threshold)) - 1)
    while candidate > 0 and not (
        math.sqrt((2.0 * candidate) ** k / float(n))
        + C_ALPHA / math.sqrt(float(n))
        + float(tv_hat)
        < 0.5
    ):
        candidate -= 1
    while (
        math.sqrt((2.0 * (candidate + 1)) ** k / float(n))
        + C_ALPHA / math.sqrt(float(n))
        + float(tv_hat)
        < 0.5
    ):
        candidate += 1
    return candidate


def m_max_table():
    return [
        {
            "tv_hat": tv,
            "rows": [
                {
                    "k": k,
                    "M_max_by_n": {str(n): m_max(k, n, tv) for n in N_VALUES},
                }
                for k in K_WINDOW
            ],
        }
        for tv in TV_VALUES
    ]


table = k_table()
report = {
    "report_metadata": {
        "generated_at_utc": "2026-09-13 12:24:50 UTC",
        "project_root": str(ROOT),
        "calculation_library": "NumPy plus Python standard-library JSON/math",
        "sample_size_assumption_for_tables": "n1 = n2 = n",
        "k_search_range": [1, 30],
        "pre_registered_window": [5, 15],
    },
    "criterion_formula": {
        "general": "For m=(2M)^k: 0.5*sqrt(m/n1) + 0.5*sqrt(m/n2) + 0.5*sqrt(2*log(2/alpha)/n1) + 0.5*sqrt(2*log(2/alpha)/n2) < 0.5 - tv_hat.",
        "per_law_radius": "r_i(k) = 0.5*sqrt((2M)^k/n_i) + 0.5*sqrt(2*log(2/alpha)/n_i).",
        "verdict": "tv_hat + r_1(k) + r_2(k) < 0.5.",
        "equal_n_reduction": "With n1=n2=n, tv_hat + sqrt((2M)^k/n) + sqrt(2*log(2/alpha)/n) < 0.5.",
        "k_cert_definition": "k_cert is the largest integer k in 1..30 satisfying the strict inequality; null means no positive k satisfies it.",
        "alpha": ALPHA,
        "c_alpha": C_ALPHA,
        "guarantee": "The upper-side radius is a finite-sample statement only when the alphabet is fixed a priori and the sampling conditions hold."
    },
    "k_cert_table": {
        "columns": ["M", "n1_equals_n2", "k_cert(tv_hat=0.1)", "k_cert(tv_hat=0.2)", "k_cert(tv_hat=0.3)", "k_cert(tv_hat=0.4)"],
        "rows": table,
    },
    "k_cert_in_window": {
        "window": [5, 15],
        "rows": in_window_rows(table),
        "summary": "The listed (M,n,tv_hat) combinations have k_cert in the pre-registered window. Combinations not listed fail the window test, either because k_cert<5 or because no positive k survives; no listed k_cert exceeds 15."
    },
    "M2_assessment": {
        "a_priori_confirmed": True,
        "reasoning": "Yes. The 1200-byte boundary is fixed before observing the dataset: RFC 9000 requires a client Initial datagram to carry a UDP payload of at least 1200 bytes. The split {<=1200, >1200} therefore uses a protocol-specified constant, not a sample quantile, realized support, or any other dataset statistic. This does not assert that every implementation or coalescing pattern has identical behavior; those are measurement limitations, not data-dependent bin selection.",
        "alphabet": "Two size bins times two directions gives four per-datagram symbols and m_grid=4^k.",
        "k_cert_by_n": [
            {
                "n1_equals_n2": n,
                "k_cert_by_tv_hat": {str(tv): k_cert(2, n, tv) for tv in TV_VALUES},
            }
            for n in N_VALUES
        ],
        "what_is_lost": {
            "size_distinctions": "All sizes <=1200 are merged into one symbol and all sizes >1200 are merged into one symbol. Exact lengths, distinctions among sizes below or equal to 1200, distinctions among sizes above 1200, and any finer size-bin transitions disappear; direction remains observable.",
            "object_described": "The resulting bracket is for the TV distance between the two laws of the coarsened direction-plus-thresholded-size k-prefix, not the full QUIC wire-image k-prefix.",
            "support_comparison": "At k=6, the fine base-64 full grid has 64^6=68,719,476,736 cells, while the M=2 grid has 4^6=4,096 cells. The supplied fine-grid observation is about 2,500 realized prefixes. The M=2 realized support is at most its own a-priori 4,096-cell grid; it can be compared numerically with the approximately 2,500 fine-grid count only after reading the data. The inequality M=2 support <= fine-grid support is valid only if the 1200-byte representation is proven to be a deterministic coarsening of the exact fine-grid symbols, which is not assumed here. Neither realized count is substituted into m.",
            "m_rule": "For every k, m remains the fixed a-priori value 4^k, regardless of how many symbols are realized."
        },
        "verdict": "M=2 reaches [5,15] for some requested settings, but not universally. It fails at n=1e3 for every tv_hat, and it fails the window at several higher-n/high-tv_hat settings shown in the table. Among the requested settings, it reaches the window at n=1e4,tv_hat=0.1; at n=1e5,tv_hat in {0.1,0.2,0.3}; at n=1e6 for all four tv_hat values; and at n=1e7 for all four tv_hat values. This is an honest conditional pass, not a claim that the M=2 design passes for every sample size or estimate."
    },
    "M_max_by_k_and_n": {
        "definition": "For equal n, let B=0.5-tv_hat-sqrt(2*log(2/alpha)/n). If B<=0, no positive M survives. Otherwise (2M)^k < n*B^2, hence M < 0.5*(n*B^2)^(1/k). M_max is the largest positive integer satisfying this strict inequality, or 0 if none exists.",
        "k_range": [5, 15],
        "n_columns": N_VALUES,
        "tables_by_tv_hat": m_max_table(),
    },
    "per_k_table_columns": [
        {
            "column": "k",
            "definition": "Prefix length in observable datagrams; this report evaluates k=1..30 and highlights the pre-registered k=5..15 window."
        },
        {
            "column": "m_grid",
            "definition": "The fixed a-priori product-grid cardinality used as m in the concentration bound: (2M)^k."
        },
        {
            "column": "m_reachable_a_priori",
            "definition": "Any smaller protocol-proven upper bound on reachable k-prefix symbols that can be established without inspecting data. None is established here beyond the product-grid bound, so use m_reachable_a_priori=(2M)^k and do not claim a smaller value."
        },
        {
            "column": "realized_support",
            "definition": "The observed number of distinct k-prefix symbols in the sample, reported only for transparency. It is data-dependent and is never substituted into m."
        },
        {
            "column": "radius",
            "definition": "Per-law finite-sample concentration radius r_i=0.5*sqrt(m_grid/n_i)+0.5*sqrt(2*log(2/alpha)/n_i); report radius_1 and radius_2 when sample sizes differ."
        },
        {
            "column": "eps_hi",
            "definition": "The plug-in point estimate plus both concentration radii: tv_hat + radius_1 + radius_2."
        },
        {
            "column": "verdict",
            "definition": "Certificate survives exactly when tv_hat + radius_1 + radius_2 < 0.5. Testing radius<0.5 alone is insufficient and does not certify the claimed upper bound."
        }
    ],
    "verdict": "The full product grid must use the fixed a-priori m=(2M)^k; realized support is transparency only. With the requested equal-n calculation, coarse fixed quantization can leave a non-empty finite-sample upper-side certificate in k=5..15, while finer M values generally lose it. M=2 is defensible as a protocol-fixed 1200-byte split and conditionally reaches the window, but the certificate then concerns the deliberately coarsened observable channel.",
    "honest_framing_sentence": "When the pass holds only under coarse M, the bracket describes a deliberately coarsened observable channel, not the full QUIC wire image.",
    "known_limitations": [
        "The requested n table is interpreted as n1=n2=n; unequal sample sizes must use the general four-term criterion directly.",
        "The calculation establishes no tighter protocol-derived reachable subset than the full (2M)^k product grid.",
        "The exact M=2 realized support is not available from the supplied prompt and must be read from the actual data artifact if reported.",
        "A protocol-specified 1200-byte threshold does not remove implementation variation, packet coalescing, or the distinction between UDP payload length and any alternative extraction field; the observable definition must be fixed consistently.",
        "The upper-side finite-sample guarantee depends on the fixed-alphabet sampling assumptions. The project's classifier-based lower side is asymptotic and must not be conflated with this finite-sample upper-side certificate.",
        "A certificate on the coarsened prefix is not a certificate on the uncoarsened full wire image; this follows from the information lost by the deterministic quantization."
    ],
    "blockers": []
}

OUT.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
print(OUT)
