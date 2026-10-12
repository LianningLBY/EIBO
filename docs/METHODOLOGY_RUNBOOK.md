# EIBO 学校服务器实验启动说明

This first stage uses tracked k=5 count tables, so no raw corpus or GPU is needed.
It prepares strong classical baselines before work on representation-loss control.
It does not change the manuscript or upgrade its sampling assumptions.

## 当前环境

项目目录为 `/data/xjw/EIBO`，继续使用当前已激活的 `traffic-ncde` 环境。先检查解释器和已有依赖：

```bash
which python
python --version
python -c "import numpy, scipy; print('numpy', numpy.__version__, 'scipy', scipy.__version__)"
```

脚本使用兼容 Python 3.8 的语法，依赖范围为 NumPy 1.22 至 1.x、SciPy 1.8 至 1.x。目录为空时克隆代码，再安装缺少的依赖并运行：

```bash
git clone --branch codex/methodology-risk-certificates git@github.com:LianningLBY/EIBO.git /data/xjw/EIBO
cd /data/xjw/EIBO
python -m pip install -r requirements-methodology.txt
python -m unittest discover -s tests -p test_riskcert.py -v
python scripts/methodology_baselines.py --out artifacts/methodology/baselines_20261012_01.json
```

已有仓库时，先执行 `git fetch origin`，再执行 `git switch codex/methodology-risk-certificates` 和 `git pull --ff-only`。

每次运行使用新的输出文件名，脚本会拒绝覆盖已有结果。已有依赖满足要求时可以跳过安装。
If the server cannot access GitHub, transfer this checkout to
the project folder first; all subsequent commands run offline after dependencies
have been installed.

## What is computed

- A direct multiclass risk floor using per-service TV deviation radii and a union
  bound. The radii are obtained by calling `eibo.statcore.tv_upper_bound`.
- A second direct floor from concavity and bounded differences. This requires
  mutual independence across all services, a stronger assumption, and is reported
  separately.
- A weighted Hunter spanning-tree floor from simultaneously valid pairwise TV
  upper bounds, including a sample-count and TV reconciliation with the ledger.
- Original uniform and LP values as references under their original prior.

Known services have total prior `1 - unknown_prior`. Unknown error is discarded;
its law is neither estimated nor assumed close to the known laws. The default is
the paper's uniform prior on 45 known services plus one unknown class. The optional
`--unknown-prior` changes that mass while keeping known classes uniform.

## Interpretation and next stage

All floors concern the declared quantized observable. They cannot be compared as
certificates against detectors using additional packet-size or timing features.
Aggregate tables contain no timestamps, so this stage cannot verify temporal
splits, clustering, or deployment shift. A report is exploratory until reviewed
and registered in the project evidence chain.

The next raw-data stage should use explicit time periods and buffer intervals,
fit a frequency classifier on training counts, and evaluate it on disjoint test
counts. Representation selection must use a separate pilot set. Any certificate
for a finer observable must account for representation loss; merely certifying a
coarse representation does not certify the original observable.
