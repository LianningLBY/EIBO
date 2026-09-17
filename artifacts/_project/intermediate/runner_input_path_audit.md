# Runner Input-Path Audit

**Audit timestamp:** 2026-09-14 16:53:56 UTC  
**Execution tree:** server `111`, account `root`, project `/root/eibo`  
**Control-plane tree:** `/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade`

## Runner inventory

There are **19 unique root experiment/control runners** in this checkout:

| Cohort | Runners |
|---|---|
| Named cohort | `x6_divisibility_lower_bound.py`, `x3_axis_validation.py`, `x3_parametric_growth.py`, `x12_detector_validation.py`, `x11_feasibility_probe.py`, `x9_sni_channel_delta.py`, `x9_dose_response_channels.py`, `x9_cardinality_control.py` |
| Additional runners | `q1_eps_lo_symbol_map.py`, `e7_phist_certificate.py`, `q2_phist_certificate_v3.py`, `x5_estimator_ground_truth.py`, `x3_controls.py`, `x3_positionwise_null.py`, `x3_control_heterogeneous_iid.py`, `x3_control_occupancy_dose_response.py`, `x3_variant_a_estimator_family.py`, `x3_variant_b_support_conditioning.py`, `x3_variant_c_nested_lr.py` |

The intermediate directory contains snapshots of the X3/X6/X9/X12 runners, including `artifacts/_project/intermediate/x3_controls.py`, `x3_control_occupancy_dose_response.py`, `x3_variant_a_estimator_family.py`, `x3_variant_b_support_conditioning.py`, `x3_variant_c_nested_lr.py`, `x6_divisibility_lower_bound.py`, `x9_sni_channel_delta.py`, `x12_detector_validation.py`, and `x3_axis_validation.py`. They do not add unique runner identities; their path constants were checked against the same server tree.

`x5_estimator_ground_truth.py` has no runtime filesystem input; it uses synthetic constants and only writes its JSON artifact.

## Server artifact layout

The decisive server layout is flat under `/root/eibo/artifacts/`; the relevant entries from `ls -la /root/eibo/artifacts/` are:

```text
q1_eps_lo_symbol_map.json                         1514746 bytes
q1_eps_lo_symbol_map.state.pkl                   3336380 bytes
q1_lower_side_full_n.json                         1677976 bytes
q2_phist_certificate.json                          887700 bytes
q2_phist_certificate_v2.json                      1536452 bytes
x1_headline_table.json                               32609 bytes
x3_chain_rule_divergence.json                       24249 bytes
x4_frontier_function.json                            14893 bytes
x6_divisibility_lower_bound.state.pkl              540029 bytes
x9_sni_channel_delta.json                           1928205 bytes
x11_feasibility.json                                999144 bytes
x12_detector_validation.json                       139995 bytes
```

The server also has `/dev/shm/eibo_x3_chain_rule/merged.pkl` (50,455,566 bytes), `ledger.json` (108,621 bytes), and `results.pkl` (403,564 bytes). There is no server `artifacts/X9/data/` directory.

## Input-path table

`SERVER-ONLY / absent locally` means the exact `/root/eibo/...` or `/dev/shm/...` input exists where the runner executes but the corresponding exact path is absent from the control-plane checkout. Where useful, the local snapshot counterpart is shown in the consequence column.

| runner | input path | tree that has it | exists on server? | classification | consequence |
|---|---|---|---|---|---|
| `x6_divisibility_lower_bound.py:141` | `/root/eibo/artifacts/x6_divisibility_lower_bound.state.pkl` | SERVER | yes, 540029 B | SERVER-ONLY / absent locally | Resume/chunk/finalize modes read it; absent locally would raise `FileNotFoundError`. Initial stage creates it. |
| `x6_divisibility_lower_bound.py:162-165` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache precondition is false locally; the runner refuses to proceed before expensive work. |
| `x6_divisibility_lower_bound.py:162-165` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `load_merged()` raises `FileNotFoundError` locally; server execution is OK. |
| `x6_divisibility_lower_bound.py:162-165` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache precondition is false locally; the runner refuses to proceed. |
| `x6_divisibility_lower_bound.py:642` | `/root/eibo/artifacts/q1_eps_lo_symbol_map.json` | SERVER; local snapshot `artifacts/_project/data/q1_eps_lo_symbol_map.json` | yes, 1514746 B | SERVER-ONLY / absent locally | `read_text()` and `sha256_file()` fail in a local run because the flat path is absent. |
| `x6_divisibility_lower_bound.py:643` | `/root/eibo/artifacts/x1_headline_table.json` | SERVER; local snapshot `artifacts/_project/data/x1_headline_table.json` | yes, 32609 B | SERVER-ONLY / absent locally | `read_text()` fails locally; snapshot is not at the runner's path. |
| `x6_divisibility_lower_bound.py:644` | `/root/eibo/artifacts/x4_frontier_function.json` | SERVER; local snapshot `artifacts/_project/data/x4_frontier_function.json` | yes, 14893 B | SERVER-ONLY / absent locally | `read_text()` fails locally; snapshot is not at the runner's path. |
| `x3_axis_validation.py` | no runtime filesystem input | neither | N/A | OTHER | Synthetic-only runner; no input path to test. |
| `x3_parametric_growth.py:56,280` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_parametric_growth.py:51-63` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Inventory check fails locally before real cached-sequence work. |
| `x3_parametric_growth.py:51-63` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Inventory check fails locally before real cached-sequence work. |
| `x12_detector_validation.py:412,1264` | `/root/eibo/artifacts/q1_lower_side_full_n.json` | SERVER; local snapshot `artifacts/_project/data/q1_lower_side_full_n.json` | yes, 1677976 B | SERVER-ONLY / absent locally | Conditional `--k-packets` path; `load_x1_upper_bounds()` raises `FileNotFoundError` locally. |
| `x11_feasibility_probe.py:341-345` | `/root/miniconda3/lib/python3.12/site-packages/cesnet_datazoo/datasets/metadata/metadata.csv` | SERVER | yes, 3093 B | SERVER-ONLY / absent locally | `read_text()` fails if the probe is run in the control-plane environment. No fallback; this is package metadata, not the H5 corpus. |
| `x9_sni_channel_delta.py:74` | `/root/eibo/scripts/xs_compression_early_readout.py` | BOTH | yes, 35614 B | OK | Imported helper exists in both trees. |
| `x9_sni_channel_delta.py:77-78` | `/root/eibo/src/eibo/statcore.py` | BOTH | yes, 25641 B | OK | Imported reference implementation exists in both trees. |
| `x9_dose_response_channels.py:81` | `/root/eibo/scripts/xs_compression_early_readout.py` | BOTH | yes, 35614 B | OK | Imported helper exists in both trees. |
| `x9_dose_response_channels.py:88` | `/root/eibo/src/eibo/statcore.py` | BOTH | yes, 25641 B | OK | Imported reference implementation exists in both trees. |
| `x9_dose_response_channels.py:503-508` | `/root/eibo/artifacts/x9_sni_channel_delta.json` | SERVER; local snapshot only | yes, 1928205 B | SERVER-ONLY / absent locally | This is the correct flat producer path on the current server; local checkout lacks the exact flat path. |
| `x9_dose_response_channels.py:503-508` | `/root/eibo/artifacts/X9/data/x9_sni_channel_delta.json` | LOCAL snapshot `artifacts/X9/data/x9_sni_channel_delta.json` | **no** | SNAPSHOT-ONLY (DEFECT) | Literal server result: `ls: cannot access '/root/eibo/artifacts/X9/data/x9_sni_channel_delta.json': No such file or directory`. `resolve_existing_path()` has no default/try-except; if the flat candidate is unavailable or ordered out, it raises `FileNotFoundError` after the expensive ladder. Correct producer path: `/root/eibo/artifacts/x9_sni_channel_delta.json`. |
| `x9_cardinality_control.py:88` | `/root/eibo/scripts/xs_compression_early_readout.py` | BOTH | yes, 35614 B | OK | Imported helper exists in both trees. |
| `x9_cardinality_control.py:95` | `/root/eibo/src/eibo/statcore.py` | BOTH | yes, 25641 B | OK | Imported reference implementation exists in both trees. |
| `x9_cardinality_control.py:462` | `/root/eibo/artifacts/x9_sni_channel_delta.json` | SERVER; local snapshot only | yes, 1928205 B | SERVER-ONLY / absent locally | `load_existing_artifact()` would raise `FileNotFoundError` in a local run; server execution is OK. |
| `q1_eps_lo_symbol_map.py:175,522` | `/root/eibo/artifacts/q2_phist_certificate_v2.json` | SERVER | yes, 1536452 B | SERVER-ONLY / absent locally | Vector reference is read at line 175; resume state is a separate input below. Local exact path is absent, so the reference load crashes. |
| `q1_eps_lo_symbol_map.py:522` | `/root/eibo/artifacts/q1_eps_lo_symbol_map.state.pkl` | SERVER | yes, 3336380 B | SERVER-ONLY / absent locally | `--stage compute` explicitly raises `RuntimeError` if this state path is absent. |
| `e7_phist_certificate.py:367` | `/root/eibo/artifacts/q2_phist_certificate.json` | SERVER | yes, 887700 B | SERVER-ONLY / absent locally | Optional previous-run comparison is skipped when absent; fallback is `previous_rows = []`, so this is a silent provenance/data-comparison loss rather than a crash. |
| `e7_phist_certificate.py:412` | `/root/autodl-tmp/eibo/q2_phist_certificate_v2_state.pkl` | SERVER | yes, 189385994 B | SERVER-ONLY / absent locally | If absent, code silently falls back to `state = scan_h5()`, repeating the expensive scan. |
| `q2_phist_certificate_v3.py:480` | `/root/autodl-tmp/eibo/q2_phist_certificate_v3_state.pkl` | SERVER | yes, 1922752 B | SERVER-ONLY / absent locally | If absent, code silently falls back to `state = scan_h5()`, repeating the expensive scan. |
| `x3_controls.py:69` | `/root/eibo/artifacts/x3_chain_rule_divergence.json` | SERVER; local snapshot `artifacts/_project/data/x3_chain_rule_divergence.json` | yes, 24249 B | SERVER-ONLY / absent locally | Default/main path calls `read_text()` and fails locally. |
| `x3_controls.py:70` | `/root/eibo/artifacts/q1_eps_lo_symbol_map.json` | SERVER; local snapshot `artifacts/_project/data/q1_eps_lo_symbol_map.json` | yes, 1514746 B | SERVER-ONLY / absent locally | Default/main path calls `read_text()` and fails locally. |
| `x3_controls.py:71` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | Default/main path calls `pickle.load()` and fails locally. |
| `x3_controls.py:72` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Missing file is accepted as `cached_results = {}`; this is a silent fallback, although the value is not used later in the default path. |
| `x3_positionwise_null.py:52-54,130` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally before `merged.pkl` is loaded. |
| `x3_positionwise_null.py:52-54,130` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_positionwise_null.py:52-54` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Required cache inventory fails locally. |
| `x3_control_heterogeneous_iid.py:56-76` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_control_heterogeneous_iid.py:56-76` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_control_heterogeneous_iid.py:56-76` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_control_occupancy_dose_response.py:56-76` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_control_occupancy_dose_response.py:56-76` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_control_occupancy_dose_response.py:56-76` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_a_estimator_family.py:72-99` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_a_estimator_family.py:72-99` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_variant_a_estimator_family.py:72-99` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_a_estimator_family.py:437` | `/root/eibo/artifacts/q1_eps_lo_symbol_map.json` | SERVER; local snapshot only | yes, 1514746 B | SERVER-ONLY / absent locally | Pair input read fails locally. |
| `x3_variant_a_estimator_family.py:362,431` | `/root/eibo/artifacts/x3_chain_rule_divergence.json` | SERVER; local snapshot only | yes, 24249 B | SERVER-ONLY / absent locally | Optional hash/provenance read is absent locally; server path is usable. |
| `x3_variant_b_support_conditioning.py:103-130` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_b_support_conditioning.py:103-130` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_variant_b_support_conditioning.py:103-130` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_b_support_conditioning.py:730` | `/root/eibo/artifacts/q1_eps_lo_symbol_map.json` | SERVER; local snapshot only | yes, 1514746 B | SERVER-ONLY / absent locally | Pair input read fails locally. |
| `x3_variant_b_support_conditioning.py:671,706` | `/root/eibo/artifacts/x3_chain_rule_divergence.json` | SERVER; local snapshot only | yes, 24249 B | SERVER-ONLY / absent locally | Required hash read is absent locally and can raise `FileNotFoundError`. |
| `x3_variant_c_nested_lr.py:59-65,321` | `/dev/shm/eibo_x3_chain_rule/ledger.json` | SERVER | yes, 108621 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |
| `x3_variant_c_nested_lr.py:59-65,321` | `/dev/shm/eibo_x3_chain_rule/merged.pkl` | SERVER | yes, 50455566 B | SERVER-ONLY / absent locally | `pickle.load()` fails locally. |
| `x3_variant_c_nested_lr.py:59-65` | `/dev/shm/eibo_x3_chain_rule/results.pkl` | SERVER | yes, 403564 B | SERVER-ONLY / absent locally | Cache inventory fails locally. |

## Defects

1. **X9 dose-response snapshot path:** `x9_dose_response_channels.py:503-508` includes `/root/eibo/artifacts/X9/data/x9_sni_channel_delta.json`, but the executing server has no such path. The literal check was:

   ```text
   ls: cannot access '/root/eibo/artifacts/X9/data/x9_sni_channel_delta.json': No such file or directory
   ```

   The producer output actually present on the server is `/root/eibo/artifacts/x9_sni_channel_delta.json` (1,928,205 bytes). The resolver has no default or exception fallback; if it reaches the missing snapshot candidate it crashes with `FileNotFoundError`. The observed X9_E failure is therefore a loud late failure after the dose-response loop, not a silent fallback.

2. **Control-plane/server flat-tree divergence:** 30+ server input paths are absent at their exact local `/root/eibo/...` or `/dev/shm/...` names even when the control plane has a registration snapshot under `artifacts/_project/data/` or `artifacts/X9/data/`. A local rerun would fail or rescan depending on the row; a server rerun can succeed. This is a provenance/reproducibility defect even when it does not crash the server job.

## Late preconditions

| runner | first input/precondition | expensive work before required input validation | finding |
|---|---:|---|---|
| `x6_divisibility_lower_bound.py` | 493-506 | validity loop 260-287 and real loop 370-395 are gated by cache checks | no late required-input check visible |
| `x3_axis_validation.py` | 308 | synthetic generation and Monte Carlo/report work 309-334 | **late/no meaningful input gate**; synthetic-only, so no external file crash |
| `x3_parametric_growth.py` | 254-256 | synthetic control follows cache inventory | no |
| `x12_detector_validation.py` | 1021-1035 | H5 scan/read 1053-1106 precedes the full label-cardinality/schema checks | **late semantic corpus validation** |
| `x11_feasibility_probe.py` | 341-345 / 354 | metadata then H5 probe; no separate late artifact input | no late non-corpus input visible |
| `x9_sni_channel_delta.py` | 375-383 | H5 split scan begins 384 after checks | no |
| `x9_dose_response_channels.py` | 604-606 | all original and bucket-rung computation 607-623 precedes calibration read at 661-662, which resolves candidates at 502-508 | **late required calibration input; X9_E failure pattern** |
| `x9_cardinality_control.py` | 545-552 | existing artifact is checked/read before H5 loop 555 | no |
| `q1_eps_lo_symbol_map.py` | 520-522 | compute-stage state check precedes pair work | no |
| `e7_phist_certificate.py` | 411-412 | state load/scan precedes lower-bound loop | no required-input late check; optional previous comparison is post-compute |
| `q2_phist_certificate_v3.py` | 479-480 | state load/scan precedes lower-bound loop | no |
| `x5_estimator_ground_truth.py` | 334 | convergence, coverage, bracket, scorer, and identical-law loops 348-373 | **late/no external input gate**; synthetic-only |
| `x3_controls.py` | 68-72 | `load_inputs()` precedes reproduction/control work | no |
| `x3_positionwise_null.py` | 52-54 / 130 | cache guard precedes real cached-sequence work | no |
| `x3_control_heterogeneous_iid.py` | 56-76 | cache guard precedes control work | no |
| `x3_control_occupancy_dose_response.py` | 56-76 | cache guard precedes 200k-flow/thinning work | no |
| `x3_variant_a_estimator_family.py` | 72-99 | cache guard precedes real assessment | no clear late required-input check |
| `x3_variant_b_support_conditioning.py` | 103-130 | cache guard precedes real assessment; pair input is read at 730 after computation | optional/provenance read is late, but not the primary compute precondition |
| `x3_variant_c_nested_lr.py` | 59-65 / 321 | cache guard precedes real cached-sequence work | no |

## Audit counts

- `runners_audited`: 19 unique runners; intermediate snapshots mapped to those identities.
- `input_paths_checked`: 53 file inputs, excluding the H5 corpus, output paths, `sys.path` helpers, and lock/temp paths.
- `snapshot_only_defects`: 1.
- `silent_fallback_risks`: 4: E7 previous comparison (`previous_rows = []`), E7 state (`state = scan_h5()`), Q2 v3 state (`state = scan_h5()`), and X3 `results.pkl`'s unused `cached_results = {}` fallback.
- `runners_with_late_precondition`: 4: `x3_axis_validation.py`, `x12_detector_validation.py`, `x9_dose_response_channels.py`, and `x5_estimator_ground_truth.py`.
