# X9_E Dose-Response Channels Analysis

Generated: 2026-09-14 18:24:56 UTC

## Artifact Provenance

- Experiment: `X9_E`
- Source JSON: `/root/eibo/artifacts/x9_dose_response_channels.json`
- Server: `111`
- Account: `root`
- Size: `19209325` bytes
- SHA256: `7bca0a93b0b933e949b8a797a127e641140fda2aa226a22894495cd1f9179c49`
- Recorded outcome: `MEASURED_DOSE_RESPONSE_CHANNELS`
- Runner: `/root/eibo/x9_dose_response_channels.py`
- Runner SHA256: `3db1b28edba5803288cf4337b6ef26aa45abbc34ee9550676f1df9226554cd50`
- Source H5: `/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5`
- Source H5 size recorded in artifact: `3544625537` bytes
- Execution: CPU-only (`cuda_touched: false`), elapsed before write `1876.8864891529083` seconds

## Interpretation Conventions

- `B_*` is the SNI-dependent arm: `k=5` prefix plus `hash_B(DST_IP)`.
- `C_*` is the SNI-independent arm: `k=5` prefix plus `hash_B(random_id)`.
- Declared alphabet size is a priori and fixed as `m=32*B`; realized support is information only and is not used as `m`.
- `delta_tv_hat` is the matched-pair median of `tv_hat(B_*) - tv_hat(C_*)`. The artifact marks it as a valid radius-free measurement at every rung, including clipped rungs.
- `eps_hi` is the upper-side result from `eibo.statcore.tv_upper_bound`, with `alpha_per_law=0.025`. Its pairwise delta is reported as `comparison_unavailable` unless all 703 matched pairs are non-clipped; that condition is false at every rung.
- `eps_lo` is absent from the artifact at both arm-summary and pair-row levels (`0` occurrences). The bound convention records only the trivial lower endpoint `0.0` and the upper side/radius-free measurement. Therefore this artifact is not a two-sided bracket.
- The upper-side guarantee is finite-sample; no asymptotic lower-bound guarantee is supplied by this runner.

## Pair Completeness

The JSON contains both `train` and `test` split results. Every rung has `703` pair rows in each split, and every arm summary has `observation_count=703`.

- Train months: `202406`, `202407`, `202408`, `202409`, `202410`, `202411`
- Test months: `202501`, `202502`, `202503`, `202504`, `202505`
- Split verification recorded in the artifact: flow-disjoint `true`, time-disjoint `true`

## Matched-B Comparison

All values below are exact JSON floating-point values. `both-nonclipped pairs` is counted from the artifact's per-pair `both_arms_nonclipped` flags. `both saturated` is the conjunction of the two arm-summary `saturated` fields.

| B | Declared m | Split | SNI-dependent tv_hat median | SNI-independent tv_hat median | Matched delta tv_hat median | SNI-dependent eps_hi median | SNI-independent eps_hi median | SNI-dependent clipped fraction | SNI-independent clipped fraction | Both-nonclipped pairs | Both saturated |
|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 2 | 64 | train | 0.6185851584524288 | 0.5243006801211006 | 0.03212729493028871 | 0.6807860234066085 | 0.5786128166330645 | 0.07254623044096728 | 0.04836415362731152 | 652 | false |
| 2 | 64 | test | 0.6661738095294717 | 0.5880686208530725 | 0.027135967874048372 | 0.7372252878228774 | 0.6616691475389438 | 0.11095305832147938 | 0.07539118065433854 | 625 | false |
| 4 | 128 | train | 0.7019651585545532 | 0.5243006801211005 | 0.10147044913654757 | 0.787169144786505 | 0.5998567747302767 | 0.13940256045519203 | 0.06543385490753911 | 605 | false |
| 4 | 128 | test | 0.7368658720075265 | 0.5880800854324502 | 0.08850312011085504 | 0.8258384939438201 | 0.6864685334145756 | 0.18207681365576103 | 0.11095305832147938 | 575 | false |
| 16 | 512 | train | 0.8768009217879428 | 0.5264858111113624 | 0.2725000217883691 | 1.0 | 0.6764723120630853 | 0.5391180654338549 | 0.15362731152204837 | 324 | false |
| 16 | 512 | test | 0.8892443640857763 | 0.5885820027367983 | 0.22707038161795523 | 1.0 | 0.7634243917001378 | 0.615931721194879 | 0.2147937411095306 | 270 | false |
| 256 | 8192 | train | 0.995668179818517 | 0.5503996514289411 | 0.3580031512695009 | 1.0 | 1.0 | 0.9544807965860598 | 0.631578947368421 | 32 | false |
| 256 | 8192 | test | 0.9953078207983638 | 0.6122874142536033 | 0.3136358129355896 | 1.0 | 1.0 | 0.968705547652916 | 0.7396870554765291 | 22 | false |
| 65536 | 2097152 | train | 1.0 | 0.975121016538927 | 0.0174694325257283 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | true |
| 65536 | 2097152 | test | 1.0 | 0.9792477583732331 | 0.015021480568041645 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | true |
| 256^10 (`1208925819614629174706176`) | 38685626227668133590597632 | train | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | true |
| 256^10 (`1208925819614629174706176`) | 38685626227668133590597632 | test | 1.0 | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | true |

`delta_eps_hi` is `comparison_unavailable` for all 12 split/rung rows in the artifact. The arm medians are still reported above, but subtracting those medians is not the artifact's quotable paired upper-bound comparison.

## Realized Support Diagnostics

These values are explicitly information-only diagnostics and are not the declared alphabet size.

| B | Split | Arm | Mean pair-union support | Maximum pair-union support |
|---:|:---:|:---:|---:|---:|
| 2 | train | SNI-dependent | 31.70697012802276 | 32 |
| 2 | train | SNI-independent | 31.84921763869132 | 32 |
| 2 | test | SNI-dependent | 31.09103840682788 | 32 |
| 2 | test | SNI-independent | 31.463726884779515 | 32 |
| 4 | train | SNI-dependent | 62.31294452347084 | 64 |
| 4 | train | SNI-independent | 63.48933143669986 | 64 |
| 4 | test | SNI-dependent | 59.78947368421053 | 64 |
| 4 | test | SNI-independent | 61.93598862019915 | 64 |
| 16 | train | SNI-dependent | 210.83783783783784 | 256 |
| 16 | train | SNI-independent | 249.90327169274536 | 256 |
| 16 | test | SNI-dependent | 187.42958748221906 | 256 |
| 16 | test | SNI-independent | 234.60170697012802 | 256 |
| 256 | train | SNI-dependent | 1171.5206258890469 | 4023 |
| 256 | train | SNI-independent | 3464.0028449502133 | 4096 |
| 256 | test | SNI-dependent | 884.0426742532005 | 3677 |
| 256 | test | SNI-independent | 2894.25320056899 | 4080 |
| 65536 | train | SNI-dependent | 3079.7610241820767 | 34038 |
| 65536 | train | SNI-independent | 144841.17211948792 | 437975 |
| 65536 | test | SNI-dependent | 2276.7852062588904 | 26068 |
| 65536 | test | SNI-independent | 112068.07396870555 | 348494 |
| 256^10 | train | SNI-dependent | 3133.805120910384 | 35220 |
| 256^10 | train | SNI-independent | 250376.15789473685 | 1414770 |
| 256^10 | test | SNI-dependent | 2318.8477951635846 | 26936 |
| 256^10 | test | SNI-independent | 200298.26315789475 | 1153365 |

## Saturation and Clipping

- First rung where both arms are fully saturated: `B=65536`, declared `m=2097152`, in both train and test (`clipped_fraction=1.0` for both arms).
- The extreme `B=256^10` rung is also fully saturated in both splits.
- At `B=16`, the SNI-dependent arm is not fully saturated (`clipped_fraction=0.5391180654338549` train and `0.615931721194879` test), but its `eps_hi` median is already `1.0`; this is majority clipping, not full-rung saturation.
- At `B=256`, both arm medians of `eps_hi` are `1.0`, while neither arm is fully saturated. Only `32` train and `22` test matched pairs remain jointly non-clipped.
- The artifact's arithmetic labels mark `B=65536` and `B=256^10` as forced-clip rungs in both splits.
- The representative-pair strict `radius_sum < 1.0` thresholds recorded by the runner are:
  - Train: largest informative `B=10399`, corresponding `m=332768`
  - Test: largest informative `B=7363`, corresponding `m=235616`

## Hypothesis Evaluation

### Result: FALSIFIED for the dose-only/move-together hypothesis

The arms do not move together at matched declared `m` before full saturation:

- At `B=2`, matched median `delta_tv_hat` is `0.03212729493028871` train and `0.027135967874048372` test.
- At `B=4`, it increases to `0.10147044913654757` train and `0.08850312011085504` test.
- At `B=16`, it is `0.2725000217883691` train and `0.22707038161795523` test.
- At `B=256`, it is `0.3580031512695009` train and `0.3136358129355896` test.

These are meaningful separations in the radius-free measurement while both arms remain `saturated=false` at the rung-summary level. The strongest non-fully-saturated separation is at `B=256`, but its upper-side medians are already clipped (`eps_hi` median `1.0` for both arms), so the `tv_hat` comparison is the informative quantity there.

At `B=65536` and above, both arms saturate and the matched `delta_tv_hat` collapses to `0.0174694325257283` train, `0.015021480568041645` test, and then `0.0` at `B=256^10`. Those high-rung differences cannot be used to support dose-only co-movement because both upper sides are clipped.

The artifact's embedded prediction metadata independently records `verdict=CONFIRMS`, `part_ii_tv_delta_near_0_39=true`, and nearest candidate delta `0.3919878875222273`; this is consistent with an identifier-dependent channel effect, not with the user-stated move-together hypothesis.

## DST_IP / QUIC_SNI Determinism Sub-check

The artifact reports:

- Rows checked: `10000000`
- Distinct `DST_IP`: `33761`
- Distinct `QUIC_SNI`: `93735`
- `DST_IP` values mapping to more than one `QUIC_SNI`: `13111`
- `QUIC_SNI` values mapping to more than one `DST_IP`: `8323`
- `derivation_direction`: `DST_IP is not a function of QUIC_SNI`
- `derivation_holds`: `false`

Therefore the tested deterministic-function premise does not hold. In particular, `8323` distinct `QUIC_SNI` values map to multiple `DST_IP` values in the checked rows, directly refuting `DST_IP = f(QUIC_SNI)` for this artifact's data.

## Registry-Ready Numbers

- Experiment outcome: `MEASURED_DOSE_RESPONSE_CHANNELS`
- Hypothesis status under the stated falsification criterion: `FALSIFIED`
- Pair count: `703` per rung per split
- Splits: train and test; flow-disjoint and time-disjoint
- First full saturation of both arms: `B=65536`, `m=2097152`
- Train matched `delta_tv_hat` medians at `B=[2,4,16,256]`: `[0.03212729493028871, 0.10147044913654757, 0.2725000217883691, 0.3580031512695009]`
- Test matched `delta_tv_hat` medians at `B=[2,4,16,256]`: `[0.027135967874048372, 0.08850312011085504, 0.22707038161795523, 0.3136358129355896]`
- Train/test `delta_eps_hi`: `comparison_unavailable` at every rung
- `eps_lo`: absent; no two-sided interval is emitted
- Determinism premise: `derivation_holds=false`
- Determinism counts: `rows_checked=10000000`, `QUIC_SNI -> multiple DST_IP=8323`, `DST_IP -> multiple QUIC_SNI=13111`

## Caveats and Limitations

1. This artifact measures a radius-free plug-in TV estimate (`tv_hat`) and a finite-sample upper side (`eps_hi`); it does not provide a nontrivial lower side or a two-sided certificate.
2. The upper-bound alphabet size is the declared a-priori `m=32*B`; realized support values must not be substituted for it.
3. `eps_hi` is heavily clipped at larger `B`; the `B=16` and `B=256` arm medians of `eps_hi` are not informative as unclipped upper-side comparisons.
4. Pairwise `delta_eps_hi` is unavailable under the artifact's all-pairs non-clipping rule. The reported hypothesis evidence uses the artifact-designated valid `delta_tv_hat`.
5. The determinism sub-check is based on `10000000` checked rows from the H5 `flows` table; it establishes the observed mapping property for those rows, not a universal protocol-level statement.
6. The embedded outcome/prediction metadata is recorded separately from this analysis verdict. The analysis verdict applies specifically to the user-stated hypothesis that the two arms should move together as declared `m` grows.
