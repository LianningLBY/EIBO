#!/usr/bin/env bash
# Run from an environment with NumPy, SciPy, and scikit-learn.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive=${1:-data/fusion_sensor/kuhar-trimmed.zip}
url='https://data.mendeley.com/public-files/datasets/45f952y38r/files/49c6120b-59fd-466c-97da-35d53a4be595/file_downloaded'
checksum='9fe5d0052f2f1d6711afac42ee4badd968116afa8ba4b8ba591f4fdd771c2ec2'

python -c 'import numpy, scipy, sklearn'
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -u scripts/fusion_block_dependence.py \
    --out "artifacts/methodology/fusion_block_dependence_$stamp.json"

if [[ ! -f "$archive" ]]; then
    mkdir -p "$(dirname "$archive")"
    partial=$(mktemp "$archive.part.XXXXXXXX")
    trap 'rm -- "$partial"' EXIT
    if ! curl -fsSL --retry 3 --connect-timeout 15 --max-time 900 -o "$partial" "$url"; then
        curl -fsSL --noproxy '*' --retry 3 --connect-timeout 15 --max-time 900 -o "$partial" "$url"
    fi
    printf '%s  %s\n' "$checksum" "$partial" | sha256sum -c -
    mv -- "$partial" "$archive"
    trap - EXIT
fi

python -u scripts/fusion_kuhar_certificate.py --archive "$archive" \
    --out "artifacts/methodology/fusion_kuhar_$stamp.json"
