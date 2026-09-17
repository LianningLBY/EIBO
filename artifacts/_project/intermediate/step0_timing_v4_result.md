1) FIRST COMMAND VERBATIM: Python 3.12.3
PY_EXIT:0
DEPS-OK 2.3.2 1.18.1
DEPS_EXIT:0
bash: line 1: /usr/bin/python3: No such file or directory
WORKING INTERPRETER: /root/miniconda3/bin/python3
DEPS: numpy 2.3.2; scipy 1.18.1; tables imported successfully
SCRIPT sha256: 387d70e2194f6bc0074e636266b905bf1baa367f685517bc19bc06d5a44591aa
TIMING-ONLY MODE: NONE — default invocation (source has no argparse/add_argument/sys.argv timing flag; main() runs by default)
RUN COMMAND: cd /root/eibo && timeout 1200 /root/miniconda3/bin/python3 coverage_calibration_timing.py; echo "EXIT:$?"
RUN RESULT: COMPLETED — JSON {"output":"/root/eibo/artifacts/coverage_calibration.json","timing":{"n_a":3900000,"n_b":3900000,"per_lower_s":7.959362111985683,"per_replicate_s_at_timed_n":8.759073588997126,"per_upper_s":0.7997114770114422,"projected_total_hms":"131h 23m 10s","projected_total_s":472989.9738058448,"projection_basis":{"iid_equal_cells":45,"minimum_replicate_calls_before_dependent_arm":54000,"note":"Projection uses the measured n=3,900,000 cost for every replicate and excludes the dependent arm because B is selected only after autocorrelation measurement.","replicates_per_cell":1000,"unequal_cells":9}}}
WHAT ACTUALLY RAN: timing-only stop; the full scan did not run
TIMING NUMBERS: n_a=3900000; n_b=3900000; per_lower_s=7.959362111985683; per_upper_s=0.7997114770114422; per_replicate_s_at_timed_n=8.759073588997126; projected_total=472989.9738058448 s (131h 23m 10s); timing cell lower_eps_lo=0.09886408457698417; upper_eps_hi=0.10440634409899796
WALL CLOCK: 11.56 s (SSH tool elapsed time)
OUTPUT FILE: /root/eibo/artifacts/coverage_calibration.json size 3588 sha256 26ac24719b21d15ae628da2fb92efeac5823ca1a6fe50c51ec754bdcbfaed767
OUTPUT CONTENT: iid rows 0 | dependent rows 0 | declined_monotonically not present (JSON field absent; measured_autocorrelation empty) | runner.sha256 not present
SCRIPT MODIFIED: no
BLOCKERS: none for timing-only measurement; full calibration scan intentionally not executed because the timing projection is approximately 131h 23m
