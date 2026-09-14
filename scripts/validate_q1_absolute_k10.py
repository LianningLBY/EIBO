import collections, csv, hashlib, json
from pathlib import Path

BASE = Path('/root/eibo/artifacts')

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    rows = json.loads((BASE / 'q1_absolute_counts_k10.json').read_text())['pairs']
    keys = {'service_a', 'service_b', 'M', 'n_a', 'n_b', 'tv_k10_masked'}
    assert len(rows) == 4950
    assert all(set(row) == keys for row in rows)
    assert all(int(row['service_a']) < int(row['service_b']) for row in rows)
    assert len({(r['service_a'], r['service_b'], r['M']) for r in rows}) == 4950
    assert collections.Counter(r['M'] for r in rows) == collections.Counter({m: 990 for m in (1, 2, 4, 8, 16)})
    csv_rows = list(csv.DictReader(open(BASE / 'q1_absolute_counts_k10.csv', newline='')))
    assert len(csv_rows) == 4950
    assert all(set(row) == keys for row in csv_rows)
    meta = json.loads((BASE / 'q1_absolute_counts_k10.meta.json').read_text())
    summary = json.loads((BASE / 'q1_absolute_k10_summary.json').read_text())
    assert meta['k'] == 10 and meta['row_count'] == 4950
    assert meta['pairing']['services_retained'] == 45
    assert meta['k10_denominator_exactness']['post_mask_usable_pairs'] == 990
    assert meta['pairing']['service_threshold'].endswith('PPI_LEN >= 10; SELF-DEFINED')
    assert len(summary['per_rung']) == 5
    for item in summary['per_rung']:
        assert item['pairs'] == 990
        assert item['lower_side_fraction'] >= 0 and item['upper_side_fraction'] >= 0
        assert item['gate_fraction_both'] >= 0
    print(json.dumps({
        'rows': len(rows),
        'm_counts': dict(collections.Counter(r['M'] for r in rows)),
        'summary_rungs': len(summary['per_rung']),
        'source_h5_sha256': meta['source_h5']['sha256'],
        'artifact_sha256': {name: digest(BASE / name) for name in (
            'q1_absolute_counts_k10.json', 'q1_absolute_counts_k10.csv',
            'q1_absolute_counts_k10.meta.json', 'q1_absolute_k10_summary.json')},
    }, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
