import json


PATH = "/root/eibo/artifacts/x8_vector_law_tv.json"
NOTE = (
    "The DPI check compared a LOWER BOUND (vector Michel HPLB) against a POINT "
    "ESTIMATE (pooled tv_hat). A lower bound below a point estimate is expected "
    "and does not falsify DPI. 0 violations means 0/990 testable, NOT 990/990 "
    "passed. This is a sanity smoke-test, not a falsifiable DPI verification. "
    "Do NOT cite as theorem verification."
)


with open(PATH) as f:
    data = json.load(f)

if "dpi_violations_vector_vs_pooled" in data:
    data["dpi_smoke_test_violations"] = data.pop("dpi_violations_vector_vs_pooled")

if "dpi_sanity_pass_pairs" in data:
    data["dpi_smoke_test_testable_pairs"] = 0
    del data["dpi_sanity_pass_pairs"]

data.pop("pairs_where_dpi_check_can_falsify", None)
data["D091_dpi_relabel"] = NOTE

with open(PATH, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
