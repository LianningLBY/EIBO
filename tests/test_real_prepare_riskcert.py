"""Time clipping, isolation, identifier audits and H5 preparation checks."""

import argparse
import datetime as dt
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from eibo.realdata import (DAY, FlowSource, IdentifierSample, PreparationAudit, chronological_windows,
                           opaque_key, whole_interval_mask)
from methodology_real_prepare import run


DTYPE = np.dtype([("APP", "i2"), ("PPI", "i4", (3, 30)), ("PPI_LEN", "u2"),
                  ("TIME_FIRST", "f8"), ("TIME_LAST", "f8"), ("ID", "u8"),
                  ("QUIC_OCCID", "S16"), ("QUIC_OSCID", "S16"), ("QUIC_MULTIPLEXED", "u2"),
                  ("DST_IP", "S24"), ("DST_PORT", "u2"), ("PROTOCOL", "u1")])
BEGIN = int(dt.datetime(2024, 6, 1, tzinfo=dt.timezone.utc).timestamp())


def rows(day, services=(0, 1)):
    values = np.zeros(len(services), dtype=DTYPE)
    values["APP"] = services
    values["PPI_LEN"] = 8
    values["TIME_FIRST"] = BEGIN + day * DAY + 3600
    values["TIME_LAST"] = values["TIME_FIRST"] + 5
    values["ID"] = np.arange(1, len(values) + 1) + day * 10
    values["QUIC_OCCID"], values["QUIC_OSCID"] = b"same-cid", b"server-cid"
    values["DST_IP"], values["DST_PORT"], values["PROTOCOL"] = b"anonymous-endpoint", 443, 17
    return values


def table_records():
    return [{"path": f"/flows/D{(dt.datetime.fromtimestamp(BEGIN + day * DAY, dt.timezone.utc)).strftime('%Y%m%d')}",
             "rows": 2, "day_seconds": BEGIN + day * DAY, "ppi_capacity": 30} for day in range(16)]


class TestRealPreparation(unittest.TestCase):
    def test_hour_rounding_guard_and_exact_timestamp_boundary(self):
        window = (0, 7200)
        np.testing.assert_array_equal(whole_interval_mask(np.array([0, 3600, 3600]), np.array([3600, 3601, 3600]), window, 3600),
                                      [True, False, True])
        self.assertFalse(whole_interval_mask(np.array([0]), np.array([7200]), window, 0)[0])

    def test_calendar_gaps_fixed_without_labels(self):
        windows = chronological_windows(table_records(), gap_seconds=DAY)
        self.assertEqual(windows["pilot"], (BEGIN, BEGIN + 8 * DAY))
        self.assertEqual(windows["certificate"], (BEGIN + 9 * DAY, BEGIN + 12 * DAY))
        self.assertEqual(windows["evaluation"], (BEGIN + 13 * DAY, BEGIN + 16 * DAY))

    def test_pilot_only_selection_and_missing_future_classes_are_not_dropped(self):
        audit = PreparationAudit(table_records(), sample_size=10)
        audit.add(rows(0, (0, 1)), 30)
        audit.add(rows(9, (0, 2)), 30)
        audit.add(rows(13, (0, 2)), 30)
        plan = audit.plan(min_pilot_flows=1)
        self.assertEqual(plan["known_service_codes"], [0, 1])
        self.assertEqual(plan["missing_known_services"]["certificate"], [1])
        self.assertEqual(plan["status"], "needs_review")
        self.assertFalse(plan["independence_established"])

    def test_global_time_units_include_cross_service_changes(self):
        audit = PreparationAudit(table_records(), sample_size=0)
        for day in (0, 9, 13):
            audit.add(rows(day), 30)
        plan = audit.plan(min_pilot_flows=1)
        diagnostics = audit.unit_diagnostics(plan)
        self.assertEqual(plan["status"], "prepared")
        for item in diagnostics:
            self.assertEqual(item["nonempty_global_blocks"], 1)
            self.assertAlmostEqual(item["squared_change_budget"], (2 / 3) ** 2)
            self.assertIn("diagnostic_only", item["status"])

    def test_empty_keys_and_reused_cids_are_not_declared_sessions(self):
        self.assertIsNone(opaque_key(b"0x0000", b"key"))
        self.assertIsNone(opaque_key(0, b"key"))
        self.assertIsNotNone(opaque_key(b"x", b"key"))
        sample = IdentifierSample(20, 0, b"key")
        records = rows(0, (0, 1))
        sample.add(records, records["TIME_FIRST"], records["TIME_LAST"], np.ones(2, dtype=bool))
        summary = sample.summary()
        self.assertFalse(summary["raw_identifiers_exported"])
        self.assertEqual(summary["field_statistics"]["ID"]["repeated_keys"], 0)
        self.assertEqual(summary["field_statistics"]["QUIC_OCCID"]["keys_across_services"], 1)
        self.assertNotIn("same-cid", json.dumps(summary))

    def test_invalid_timestamps_and_short_prefixes_excluded(self):
        audit = PreparationAudit(table_records(), sample_size=0)
        records = rows(0, (0, 1, 2, 3))
        records["TIME_FIRST"][0] = float("nan")
        records["PPI_LEN"][1] = 4
        records["TIME_LAST"][2] = records["TIME_FIRST"][2] - 1
        audit.add(records, 30)
        self.assertEqual(audit.counts["usable_records"], 1)
        self.assertEqual(audit.counts["starts_exactly_on_hour"], 2)
        self.assertEqual(audit.counts["invalid_or_out_of_capture_timestamps"], 2)

    def test_partial_scan_never_ready(self):
        audit = PreparationAudit(table_records(), sample_size=0)
        for day in (0, 9, 13):
            audit.add(rows(day), 30)
        self.assertEqual(audit.plan(min_pilot_flows=1, full_scan=False)["status"], "needs_review")

    def test_hdf5_end_to_end_uses_installed_reader(self):
        backend = None
        for candidate in ("tables", "h5py"):
            try:
                module = importlib.import_module(candidate)
                backend = candidate
                break
            except ImportError:
                continue
        if backend is None:
            self.skipTest("HDF5 integration needs tables or h5py")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as directory:
            path, out = Path(directory) / "fixture.h5", Path(directory) / "output"
            if backend == "tables":
                with module.open_file(str(path), mode="w") as handle:
                    group = handle.create_group("/", "flows")
                    for day, table in enumerate(table_records()):
                        handle.create_table(group, table["path"].split("/")[-1], obj=rows(day))
            else:
                with module.File(path, "w") as handle:
                    for day, table in enumerate(table_records()):
                        handle.create_dataset(table["path"], data=rows(day), compression="gzip")
            source = FlowSource(path, backend)
            self.assertEqual(len(source.tables()), 16)
            source.close()
            args = argparse.Namespace(h5=path, out_dir=out, backend=backend, sha256=True, expected_sha256=None,
                                      time_unit="seconds", k=5, gap_seconds=DAY, rounding_seconds=3600,
                                      identifier_sample=10, seed=0, block_seconds=[3600, 21600, DAY],
                                      max_rows=None, chunk_rows=1, min_pilot_flows=1, alpha=0.05)
            run(args)
            self.assertEqual(json.loads((out / "run.json").read_text())["status"], "complete")
            plan = json.loads((out / "experiment_plan.json").read_text())
            self.assertEqual(plan["known_service_codes"], [0, 1])
            self.assertEqual(plan["status"], "prepared")
            self.assertFalse(plan["independence_established"])


if __name__ == "__main__":
    unittest.main()
