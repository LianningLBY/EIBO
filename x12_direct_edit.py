from pathlib import Path
import os


path = Path("/root/eibo/x12_detector_validation.py")
source = path.read_text(encoding="utf-8")

old = "FLOW_KEY_BASE = 10_000_000_000\n"
assert source.count(old) == 1
source = source.replace(
    old,
    "FLOW_KEY_BASE = 10_000_000_000\nMIN_SERVICE_LABEL_CLASSES = 20\n",
)

old = "def month_of(date_name: str) -> str:\n    return date_name[:6]\n\n\ndef flow_tokens"
assert source.count(old) == 1
source = source.replace(
    old,
    '''def month_of(date_name: str) -> str:
    return date_name[:6]


def assert_month_order(train_months: set[str], test_months: set[str]) -> None:
    train_last = max(train_months)
    test_first = min(test_months)
    if not train_last < test_first:
        raise RuntimeError(
            "time-disjoint invariant failed: resolved train months "
            f"{sorted(train_months)} are not earlier than test months {sorted(test_months)}"
        )


def count_distinct_labels(nodes: list[Any], label_field: str) -> int:
    labels: set[int] = set()
    for node in nodes:
        if label_field not in node.colnames:
            raise KeyError(f"label field {label_field!r} not in HDF5 table")
        labels.update(int(value) for value in node.read(field=label_field) if int(value) >= 0)
    return len(labels)


def flow_tokens''',
)

old = 'parser.add_argument("--label-field", default="CATEGORY", choices=["APP", "CATEGORY"])'
assert source.count(old) == 1
source = source.replace(
    old,
    'parser.add_argument("--label-field", default="APP", choices=["APP", "CATEGORY"])',
)

old_split = '''            months = sorted(set(month_of(date_name) for date_name in dates))
            if len(months) < 2:
                raise RuntimeError(f"need at least two months for a time split, found {months}")
            if args.smoke:
                train_months = {months[0]}
                test_months = {months[1]}
            else:
                split_index = max(1, len(months) // 2)
                train_months = set(months[:split_index])
                test_months = set(months[split_index:])
            train_cap = None if args.max_flows is None else max(1, args.max_flows // 2)
'''
new_split = '''            months = sorted(set(month_of(date_name) for date_name in dates))
            if len(months) < 2:
                raise RuntimeError(f"need at least two months for a time split, found {months}")
            distinct_label_count = count_distinct_labels(nodes, args.label_field)
            log(
                f"LABEL_AXIS label_field={args.label_field} "
                f"distinct_classes={distinct_label_count}"
            )
            if distinct_label_count < MIN_SERVICE_LABEL_CLASSES:
                raise RuntimeError(
                    "service label cardinality guard failed: "
                    f"label_field={args.label_field!r} distinct_classes={distinct_label_count}; "
                    f"expected at least {MIN_SERVICE_LABEL_CLASSES} service classes"
                )
            if args.smoke:
                train_months = {months[0]}
                test_months = {months[1]}
                buffer_months: list[str] = []
                split_mode = "smoke"
            else:
                split_index = max(1, len(months) // 2)
                if split_index + 1 >= len(months):
                    raise RuntimeError(f"cannot derive buffered time split from months {months}")
                train_months = set(months[:split_index])
                buffer_months = [months[split_index]]
                test_months = set(months[split_index + 1 :])
                split_mode = "default_buffered"
            assert_month_order(train_months, test_months)
            log(
                f"RESOLVED_SPLIT mode={split_mode} "
                f"train_months={sorted(train_months)} "
                f"buffer_months={buffer_months} "
                f"test_months={sorted(test_months)}"
            )
            train_cap = None if args.max_flows is None else max(1, args.max_flows // 2)
'''
assert source.count(old_split) == 1
source = source.replace(old_split, new_split, 1)

old = '            "label_field": args.label_field,\n'
assert source.count(old) == 1
source = source.replace(
    old,
    '            "label_field": args.label_field,\n            "distinct_label_class_count": distinct_label_count,\n',
)

old = '            "test_months": sorted(test_months),\n'
assert source.count(old) == 2
source = source.replace(
    old,
    '            "test_months": sorted(test_months),\n            "buffer_months": buffer_months,\n',
    1,
)

old = '            f"train_months={sorted(train_months)} test_months={sorted(test_months)} "\n'
assert source.count(old) == 1
source = source.replace(
    old,
    '            f"train_months={sorted(train_months)} buffer_months={buffer_months} "\n            f"test_months={sorted(test_months)} "\n',
)

tmp = path.with_name(path.name + ".tmp")
tmp.write_text(source, encoding="utf-8")
os.replace(tmp, path)
print("edited", path)
