"""Read-only CESNET preparation: time windows, anonymous ID audits and units.

Field availability and time isolation do not establish independent units or
conditional unbiasedness. No real-traffic coverage guarantee is produced here.
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import importlib
import re

import numpy as np

from .riskcert import joint_radius_from_change_budget
from .statcore import grid_cardinality

DAY = 86400
IDENTIFIERS = ("ID", "QUIC_OCCID", "QUIC_OSCID", "QUIC_SCID", "QUIC_RETRY_SCID")
REQUIRED = {"APP", "PPI", "PPI_LEN", "TIME_FIRST", "TIME_LAST"}


class FlowSource:
    """Prefer PyTables for the dataset's compression filters; h5py is optional."""

    def __init__(self, path, backend="auto"):
        errors = []
        for name in (("tables", "h5py") if backend == "auto" else (backend,)):
            try:
                self.module = importlib.import_module(name)
                self.backend = name
                break
            except (ImportError, OSError, ValueError) as exc:
                errors.append(f"{name}: {exc}")
        else:
            raise RuntimeError("No HDF5 reader available: " + "; ".join(errors))
        self.handle = (self.module.open_file(str(path), mode="r") if self.backend == "tables"
                       else self.module.File(path, "r"))

    def close(self):
        self.handle.close()

    def tables(self):
        result = []
        if self.backend == "tables":
            nodes = [(n._v_pathname, n) for n in self.handle.walk_nodes("/", classname="Table")]
        else:
            nodes = []
            self.handle.visititems(lambda name, node: nodes.append(("/" + name, node))
                                   if isinstance(node, self.module.Dataset) and node.dtype.names else None)
        for name, node in nodes:
            names = set(node.dtype.names or ())
            if {"APP", "PPI", "PPI_LEN"}.issubset(names):
                if not REQUIRED.issubset(names):
                    raise ValueError(f"flow table {name} lacks required fields: {sorted(REQUIRED - names)}")
                match = re.fullmatch(r"/flows/D(\d{8})", name)
                if match is None:
                    raise ValueError(f"expected /flows/DYYYYMMDD table names, got {name}")
                day = dt.datetime.strptime(match[1], "%Y%m%d").replace(tzinfo=dt.timezone.utc)
                ppi_shape = node.dtype.fields["PPI"][0].shape
                if len(ppi_shape) != 2 or ppi_shape[0] != 3:
                    raise ValueError(f"unexpected PPI shape at {name}: {ppi_shape}")
                rows = int(node.nrows) if self.backend == "tables" else int(node.shape[0])
                result.append({"path": name, "rows": rows, "day_seconds": int(day.timestamp()),
                               "ppi_capacity": int(ppi_shape[1]),
                               "fields": {field: str(node.dtype.fields[field][0]) for field in sorted(names)}})
        if not result:
            raise ValueError("no flow tables found")
        return sorted(result, key=lambda record: record["path"])

    def read(self, table, start, stop):
        node = self.handle.get_node(table) if self.backend == "tables" else self.handle[table]
        return node.read(start, stop) if self.backend == "tables" else node[start:stop]


def chronological_windows(tables, *, gap_seconds=DAY, end_margin_seconds=3600):
    """Calendar 50/25/25 split, fixed before reading labels; half-open windows."""
    begin = min(t["day_seconds"] for t in tables)
    end = max(t["day_seconds"] for t in tables) + DAY
    days = (end - begin) // DAY
    split1, split2 = begin + (days // 2) * DAY, begin + (3 * days // 4) * DAY
    windows = {"pilot": (begin, split1), "certificate": (split1 + gap_seconds, split2),
               "evaluation": (split2 + gap_seconds, end)}
    if any(stop - start <= end_margin_seconds for start, stop in windows.values()):
        raise ValueError("capture period is too short for three windows, gaps and rounding margin")
    return windows


def whole_interval_mask(first, last, window, end_margin_seconds):
    start, end = window
    # TIME_LAST was shifted with TIME_FIRST. With hourly clipping, an actual
    # last packet may be up to one hour later than the stored TIME_LAST.
    ends_inside = last + end_margin_seconds <= end if end_margin_seconds > 0 else last < end
    return (first >= start) & (first < end) & ends_inside


def opaque_key(value, salt):
    """Run-local keyed digest; zero/empty-like identifiers are non-informative.

    Zero-like is a diagnostic category, not a claim that zero-length CIDs are
    prohibited by QUIC. Raw identifiers and the hashing key are never exported.
    """
    if isinstance(value, (int, np.integer)):
        if int(value) == 0:
            return None
        raw = str(int(value)).encode()
    elif isinstance(value, (float, np.floating)):
        if not np.isfinite(value) or value == 0:
            return None
        raw = repr(float(value)).encode()
    elif isinstance(value, (str, np.str_)):
        raw = str(value).strip().encode()
    elif isinstance(value, (bytes, np.bytes_)):
        raw = bytes(value).rstrip(b"\0").strip()
    else:
        array = np.asarray(value)
        if array.size == 0 or (array.dtype.kind in "biuf" and np.all(array == 0)):
            return None
        raw = array.tobytes()
    hexadecimal_body = raw[2:] if raw[:2].lower() == b"0x" else raw
    if not raw or all(character == 0 for character in raw) or (hexadecimal_body and all(character == 48 for character in hexadecimal_body)):
        return None
    return hashlib.blake2b(raw, key=salt, digest_size=16).digest()


class IdentifierSample:
    """Uniform priority reservoir over usable records; export aggregates only."""

    def __init__(self, size, seed, salt):
        self.size, self.rng, self.salt = size, np.random.default_rng(seed), salt
        self.rows = []
        self.cutoff = float("inf")
        self.seen = 0

    def add(self, records, first, last, usable):
        indices = np.flatnonzero(usable)
        self.seen += len(indices)
        if not self.size or not len(indices):
            return
        priorities = self.rng.random(len(indices))
        chosen = priorities < self.cutoff
        names = set(records.dtype.names)
        for index, priority in zip(indices[chosen], priorities[chosen]):
            keys = {name: opaque_key(records[name][index], self.salt) if name in names else None for name in IDENTIFIERS}
            endpoint = None
            if {"DST_IP", "DST_PORT", "PROTOCOL"}.issubset(names):
                parts = [opaque_key(records[name][index], self.salt) for name in ("DST_IP", "DST_PORT", "PROTOCOL")]
                if all(part is not None for part in parts):
                    endpoint = hashlib.blake2b(b"".join(parts), key=self.salt, digest_size=16).digest()
            pair = (hashlib.blake2b(keys["QUIC_OCCID"] + keys["QUIC_OSCID"], key=self.salt, digest_size=16).digest()
                    if keys["QUIC_OCCID"] is not None and keys["QUIC_OSCID"] is not None else None)
            keys["OCCID_OSCID_pair"] = pair
            keys["endpoint_OCCID_OSCID"] = (hashlib.blake2b(endpoint + pair, key=self.salt, digest_size=16).digest()
                                                if endpoint is not None and pair is not None else None)
            self.rows.append((float(priority), int(records["APP"][index]), float(first[index]), float(last[index]), endpoint, keys))
        if len(self.rows) > self.size:
            keep = np.argpartition(np.array([row[0] for row in self.rows]), self.size - 1)[:self.size]
            self.rows = [self.rows[int(index)] for index in keep]
        if len(self.rows) == self.size:
            self.cutoff = max(row[0] for row in self.rows)

    def summary(self):
        result = {}
        for field in (*IDENTIFIERS, "OCCID_OSCID_pair", "endpoint_OCCID_OSCID"):
            groups, empty = {}, 0
            for _, service, first, last, endpoint, keys in self.rows:
                key = keys[field]
                if key is None:
                    empty += 1
                    continue
                if key not in groups:
                    groups[key] = [0, set(), set(), first, last, set()]
                group = groups[key]
                group[0] += 1
                group[1].add(service)
                group[2].add(int(first // DAY))
                group[3], group[4] = min(group[3], first), max(group[4], last)
                if endpoint is not None:
                    group[5].add(endpoint)
            repeated = [group for group in groups.values() if group[0] > 1]
            result[field] = {"sample_rows": len(self.rows), "missing_or_zero_like_rows": empty,
                             "distinct_informative_keys": len(groups), "repeated_keys": len(repeated),
                             "rows_in_repeated_keys": sum(group[0] for group in repeated),
                             "keys_across_services": sum(len(group[1]) > 1 for group in repeated),
                             "keys_across_days": sum(len(group[2]) > 1 for group in repeated),
                             "keys_across_destination_endpoints": sum(len(group[5]) > 1 for group in repeated),
                             "largest_sample_group": max((group[0] for group in repeated), default=1 if groups else 0),
                             "largest_sample_span_seconds": max((group[4] - group[3] for group in repeated), default=0.0)}
        return {"sampled_records": len(self.rows), "usable_records_seen": self.seen,
                "scope": "uniform sample of usable flows; no-repeat sample does not prove global uniqueness or independence",
                "raw_identifiers_exported": False, "field_statistics": result}


class PreparationAudit:
    def __init__(self, tables, *, k=5, time_scale=1.0, gap_seconds=DAY, rounding_seconds=3600,
                 sample_size=50000, seed=20261012, salt=b"fixture", block_seconds=(3600, 21600, DAY)):
        self.tables, self.k, self.time_scale = tables, k, time_scale
        self.rounding_seconds, self.block_seconds = rounding_seconds, tuple(block_seconds)
        self.windows = chronological_windows(tables, gap_seconds=gap_seconds, end_margin_seconds=rounding_seconds)
        self.begin, self.end = min(t["day_seconds"] for t in tables), max(t["day_seconds"] for t in tables) + DAY
        self.counts = collections.Counter()
        self.daily = collections.Counter()
        self.period = {name: collections.Counter() for name in self.windows}
        self.certificate_hours = collections.Counter()
        self.sample = IdentifierSample(sample_size, seed, salt)
        self.min_time, self.max_time = None, None

    def add(self, records, capacity):
        n = len(records)
        self.counts["rows_read"] += n
        first = np.asarray(records["TIME_FIRST"], dtype=float) / self.time_scale
        last = np.asarray(records["TIME_LAST"], dtype=float) / self.time_scale
        lengths = np.asarray(records["PPI_LEN"], dtype=float)
        services = np.asarray(records["APP"])
        if first.shape != (n,) or lengths.shape != (n,) or services.dtype.kind not in "iu":
            raise ValueError("scalar numeric timestamps, PPI_LEN and integer APP fields are required")
        valid_time = np.isfinite(first) & np.isfinite(last) & (last >= first) & (first >= self.begin) & (first < self.end)
        valid_length = np.isfinite(lengths) & (lengths == np.floor(lengths)) & (lengths >= self.k) & (lengths <= capacity)
        usable = valid_time & valid_length
        self.counts["invalid_or_out_of_capture_timestamps"] += int((~valid_time).sum())
        self.counts["unusable_prefix_length"] += int((~valid_length).sum())
        self.counts["usable_records"] += int(usable.sum())
        if valid_time.any():
            lo, hi = float(first[valid_time].min()), float(first[valid_time].max())
            self.min_time = lo if self.min_time is None else min(self.min_time, lo)
            self.max_time = hi if self.max_time is None else max(self.max_time, hi)
            self.counts["valid_timestamp_records"] += int(valid_time.sum())
            self.counts["starts_exactly_on_hour"] += int(np.isclose(np.remainder(first[valid_time], 3600), 0, atol=1e-6, rtol=0).sum())
        if "QUIC_MULTIPLEXED" in records.dtype.names:
            self.counts["multiplexed_usable_records"] += int(((records["QUIC_MULTIPLEXED"] > 0) & usable).sum())
        if not usable.any():
            return
        days = np.floor(first[usable] / DAY).astype(np.int64)
        labels = services[usable].astype(np.int64)
        pairs, totals = np.unique(np.column_stack((days, labels)), axis=0, return_counts=True)
        self.daily.update({(int(day), int(label)): int(total) for (day, label), total in zip(pairs, totals)})
        assigned = np.zeros(n, dtype=bool)
        for name, window in self.windows.items():
            mask = usable & whole_interval_mask(first, last, window, self.rounding_seconds)
            assigned |= mask
            keys, numbers = np.unique(services[mask], return_counts=True)
            self.period[name].update({int(key): int(number) for key, number in zip(keys, numbers)})
            if name == "certificate" and mask.any():
                hours = np.floor(first[mask] / 3600).astype(np.int64) * 3600
                pairs, numbers = np.unique(np.column_stack((hours, services[mask])), axis=0, return_counts=True)
                self.certificate_hours.update({(int(hour), int(label)): int(number) for (hour, label), number in zip(pairs, numbers)})
        self.counts["usable_but_excluded_by_gap_or_interval_margin"] += int((usable & ~assigned).sum())
        for width in self.block_seconds:
            upper = last[usable] + self.rounding_seconds
            if self.rounding_seconds > 0:
                upper = np.nextafter(upper, -np.inf)
            crosses = np.floor(first[usable] / width) != np.floor(upper / width)
            self.counts[f"crosses_{width}s_block_under_rounding_envelope"] += int(crosses.sum())
        self.sample.add(records, first, last, usable)

    def plan(self, *, min_pilot_flows=2000, alpha=0.05, full_scan=True):
        known = sorted(service for service, n in self.period["pilot"].items() if n >= min_pilot_flows)
        missing = {name: [service for service in known if self.period[name][service] == 0]
                   for name in ("certificate", "evaluation")}
        return {"status": "prepared" if full_scan and len(known) >= 2 and not any(missing.values()) else "needs_review",
                "full_scan": full_scan, "k": self.k, "time_unit": "UTC epoch seconds after declared scaling",
                "time_rounding_envelope_seconds": self.rounding_seconds,
                "windows": {name: {"start_utc": utc(start), "end_utc_exclusive": utc(end),
                                   "start_epoch": start, "end_epoch": end} for name, (start, end) in self.windows.items()},
                "known_service_codes": known, "selection_rule": "pilot whole-interval usable flow count >= min_pilot_flows",
                "min_pilot_flows": min_pilot_flows,
                "known_prior_per_service": 1 / (len(known) + 1) if known else None,
                "unknown_prior": 1 / (len(known) + 1) if known else None,
                "missing_known_services": missing, "alpha": alpha,
                "unit_model": "global UTC time blocks across all selected services",
                "independence_established": False, "conditional_unbiasedness_established": False,
                "session_model": "not validated; CID sample is an audit, not a session assignment",
                "fixed_representations": [{"scheme": "log", "M": rung, "k": self.k,
                                           "alphabet_size": grid_cardinality("log", log_bins=rung) ** self.k}
                                          for rung in (1, 2)],
                "feature_fields": {"packet_sequence": "PPI", "length": "PPI_LEN", "direction_row": 1, "size_row": 2},
                "next_stage": "fixed-observable count extraction and pilot-trained histogram evaluation; stationarity and dependence diagnostics",
                "representation_selection": "separate pilot only; finer-observable loss is not certified"}

    def unit_diagnostics(self, plan):
        known = plan["known_service_codes"]
        if len(known) < 2 or plan["missing_known_services"]["certificate"]:
            return []
        prior = plan["known_prior_per_service"]
        result = []
        for width in self.block_seconds:
            changes, occupancy = collections.defaultdict(float), collections.Counter()
            for (hour, service), count in self.certificate_hours.items():
                if service in known:
                    bucket = hour // width * width
                    changes[bucket] += prior * count / self.period["certificate"][service]
                    occupancy[bucket] += count
            budget = float(sum(change ** 2 for change in changes.values()))
            result.append({"block_seconds": width, "nonempty_global_blocks": len(changes),
                           "known_flow_count": sum(occupancy.values()), "squared_change_budget": budget,
                           "radius_if_units_independent_and_conditionally_unbiased": float(joint_radius_from_change_budget([budget], alpha=plan["alpha"])[0]),
                           "status": "diagnostic_only; model assumptions unverified"})
        return result


def utc(seconds):
    return dt.datetime.fromtimestamp(float(seconds), tz=dt.timezone.utc).isoformat()
