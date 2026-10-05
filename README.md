# AgriPrice Monitor

**County maize–urea price monitoring and reproducible research**

Companion project for *Benchmark choice and quotation persistence in county maize–urea price monitoring: Evidence from Liaoning, China*.

This repository accompanies the county maize–urea quotation study. It contains the analysis programs, article and supplementary materials, a short project report, and independent figures. The complete Release archive adds all observation inputs, archived web responses, resampling records, and reference results required to reproduce the analysis offline.

[中文说明](README_zh.md) · [Complete package](https://github.com/ByronLi0207/liaoning-price-monitoring/releases/latest/download/agri-price-monitor.zip) · [Quick start](docs/quickstart.md) · [Table and figure replication map](docs/replication_map.md)

**Archive series DOI:** [10.5281/zenodo.23131960](https://doi.org/10.5281/zenodo.23131960).

## Study and package

We compare five historical benchmarks and three county groups, examine quotation-update histories, and reconstruct monitoring alerts on a common observation calendar. The county archive contains **9,450 maize–urea records across 315 monitoring dates**, from 5 January 2018 to 25 September 2026. The main comparison uses twelve counties, supported by 309 national price reports and 610 archived web responses.

The results show aggregate attainment ranging from **34.31% to 99.02%** across benchmarks for the original twelve counties. The combined quotation screen flags **six of twelve counties**; aggregate alerts for the six screened counties cover **zero to 131 monitoring dates**. Month indicators explain 4.97% of pre-2021 log-ratio variation and 10.48% of the residual variation after county and year effects. The diagnostic extension documents all six Jianping urea updates, national-turn matches and coverage-rule checks in [Supplement S10](reports/supplement_methods.pdf).

## Contents and distribution

| Material | Source repository | Complete Release ZIP |
| --- | --- | --- |
| Project entry point and analysis programs | Included | Included |
| Article, supplement and short report in `reports/` | Included | Included |
| Independent figures and documentation | Included | Included |
| Full `inputs/` observations and raw-response archive | In Release attachment | Included |
| Full `results/` reference outputs and resampling records | In Release attachment | Included |

**Use the Release attachment `agri-price-monitor.zip` for the complete data and results.** GitHub's automatically generated source ZIP contains the tracked repository files. The complete package includes the article, Supplements S10 and S11, all observation inputs and the reference results needed for offline reproduction. The series DOI identifies the archive; each deposited version has its own file inventory and checksum.

## Quick start

The reference computation used Python 3.12.14, Node.js 24.19.0 and the pinned Python dependencies in `environment/requirements.lock.txt`. Runtime identifiers are recorded for diagnosis and do not determine scientific equality. After extracting the Release attachment, enter its `agri-price-monitor` directory:

```bash
python scripts/project.py info
python scripts/project.py verify
python -m pip install -r environment/requirements.lock.txt
python scripts/project.py reproduce
```

Alternatively, clone the source repository and add missing data and results from the downloaded Release attachment before verification:

```bash
git clone https://github.com/ByronLi0207/liaoning-price-monitoring.git agri-price-monitor
cd agri-price-monitor
python scripts/project.py prepare --archive /path/to/agri-price-monitor.zip
python scripts/project.py verify
```

`prepare` checks archive integrity and adds missing files while preserving existing tracked content. Full analysis uses the supplied observation and reference files; no additional price download is needed. PDF export also requires LibreOffice and the documented fonts:

Scientific replay runs in `reproduction/workspace/`, keeping the packaged inputs, results, figures and reports unchanged. It compares integer counts, classifications, missingness and sampled indices exactly; floating-point quantities use a documented absolute plus relative tolerance, with the observed maximum difference reported. The seasonality comparison treats only `provenance.python` and `provenance.numpy` as informational, recording both reference and current values. Input and method hashes in the same object remain strict. Node and platform versions are recorded in execution receipts, without version-equality gates. Rebuilt Word documents are copied to `native/` for PDF export. The source-only automated tests cover accepted alert summaries, hand-calculated month-factor and quotation-timing cases, and the numerical validator; full replay uses the complete Release archive.

```bash
python scripts/project.py export
```

See the [quick start](docs/quickstart.md) for environment setup, output locations and command details.

## Replication map

[Table 1–4 and Figure 1–2](docs/replication_map.md) each have an explicit link to their inputs, responsible commands and result files. The mapping distinguishes derived result exports, checks against archived evidence, and document layout.

[![Benchmark and county-group comparison](figures/Figure_1.png)](figures/Figure_1.png)

*Figure 1. Historical benchmarks and county groups; click for the independent image.*

[![County and national urea quotation paths](figures/Figure_2.png)](figures/Figure_2.png)

*Figure 2. Jianping, Qingyuan and national urea quotation paths.*

## Documentation and reports

- [Quick start](docs/quickstart.md): package preparation, verification and execution.
- [Replication map](docs/replication_map.md): Table 1–4 / Figure 1–2 inputs, commands and outputs.
- [Data documentation](docs/data.md): specifications, units, observation states and source records.
- [Technical methods](docs/technical.md): reference construction, resampling and numerical conventions.
- [Archival deposit and review access](docs/archiving.md): complete-package deposit, DOI status and review access.
- [Results](docs/results.md) and [architecture](docs/architecture.md): findings and program structure.
- [Reports](reports/README.md): article, supplement and short project brief.

## Citation and reuse

`CITATION.cff` describes the replication software package under the repository-maintainer handle and uses the archive series DOI, **10.5281/zenodo.23131960**. Article attribution follows the author information in the accompanying manuscript.

Project code is provided under MIT; project-owned data transformations and documentation are provided under CC BY 4.0. Consult the license files for the directory-level scope. Third-party raw web responses and quoted source material retain their original rights. The PCG reference implementation retains its Apache-2.0 notice in `environment/LICENSE_PCG_APACHE_2.0.txt`.

## Supplementary validation

[Supplement S11](reports/supplement_validation.pdf) reports all sixty single-county deletions, historical-only screening followed by two later windows, and same-product references from the other eleven counties. The complete reproduction command runs these checks and compares all twelve supplementary result files. The symmetric deletions leave 53 strictly positive paired intervals and seven including zero. The five counties flagged from 2018–2020 continue to update less frequently in both later windows; all twenty long unchanged runs coincide with at least one updating peer.
