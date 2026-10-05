# Table and figure replication map

Paths below are relative to the analysis project. The complete `reproduce` entry runs these programs in `reproduction/workspace/`; newly computed outputs appear under that working copy, while the packaged reference files remain unchanged.

[English README](../README.md) · [中文说明](../README_zh.md) · [Quick start](quickstart.md) · [Technical methods](technical.md)

This map follows the actual file reads and writes in the supplied programs. Table numbering refers to `reports/manuscript.md`, `.docx` and `.pdf`. All paths below are relative to the project root.

## Prepare and run

The source repository supplies programs, reports, documentation and figures. **Complete `inputs/` and `results/` are supplied in the complete Release attachment `agri-price-monitor.zip`.** The archive series DOI is [10.5281/zenodo.23131960](https://doi.org/10.5281/zenodo.23131960). After a source checkout, add the inputs and results from the downloaded attachment and verify the package:

```bash
python scripts/project.py prepare --archive /path/to/agri-price-monitor.zip
python scripts/project.py verify
python -m pip install -r environment/requirements.lock.txt
python scripts/project.py reproduce
```

An extracted complete Release package starts with `verify`; no preparation step is needed. The full command executes the calculations, checks the reference records, redraws four figures and rebuilds Word reports in `native/`. LibreOffice PDF export is a separate step, `python scripts/project.py export`.

## Main tables

| Article item | Responsible commands | Inputs and result files |
| --- | --- | --- |
| **Table 1 — data coverage, benchmarks and county groups** | `python scripts/project.py info`; `node inputs/full_archive/code/reproduce.cjs` checks the raw archive and normalized panel; the full command checks the benchmark calculations | County observations: `inputs/normalized_prices.csv`; dates and benchmark definitions: `inputs/reference_experiments/T1_source/frozen_specification.json` and `frozen_configuration.json`; screened membership: `inputs/reference_experiments/T4b_source/frozen_retained_cohorts.json`; archive coverage: `inputs/full_archive/results/scientific_result_rates_grid_coverage.json`. The formatted table is in `reports/manuscript.md`. |
| **Table 2 — six flagged counties and representative runs** | `node inputs/full_archive/code/reproduce.cjs` reconstructs county runs and national-window evidence and compares them with archived records | Original county panel: `inputs/full_archive/data/frozen/ln_prices_original.csv`; national prices and coverage: `inputs/full_archive/data/national/nbs_prices.csv` and `coverage_rules.json`; national run evidence: `inputs/full_archive/code/product_registry.json` → `national_evidence`; county update rates and runs: `inputs/full_archive/results/county_rates_longest_runs.json` and `constant_price_runs.json`. The table selects the six documented main-screen counties and their representative urea runs. |
| **Table 3 — five benchmarks × three county groups** | `node code/replay_frozen_science.mjs` verifies the main resampling paths; `python code/mc_precision.py` writes the 15-group result export | Historical comparison input: `inputs/reference_experiments/data/county_prices.csv`; 1,999-draw records: `inputs/reference_experiments/T1_records/` and `T4b_records/`; archived summaries: `inputs/reference_experiments/figure_export/inputs/T1_summary.html` and `T4b_complete_sets_summary.html`; output: `results/primary_15_L6.json`. Monte Carlo precision is recorded separately from the paired interval. |
| **Table 4 — trigger dates and episodes** | `node code/alerts.mjs` | Input: `inputs/normalized_prices.csv`; benchmark and county calculations: `code/reference_core.js`; outputs: `results/alerts/alerts_daily.csv` and `alerts_summary.json`. The daily file supplies the date-level classifications behind every summary cell. |

Tables 1 and 2 use documented observations and archived evidence; the named checks recompute and compare the underlying quantities. They do not create separate files named `Table_1.csv` or `Table_2.csv`. Report-building programs place the existing table text into the Word documents. Table 3 and Table 4 have the explicit machine-readable exports listed above.

## Main figures

| Article item | Command | Actual plotting inputs | Figure outputs |
| --- | --- | --- | --- |
| **Figure 1 — benchmark and county-group comparison** | `python code/plot_figures.py` | `inputs/reference_experiments/figure_export/inputs/T1_summary.html` and `T4b_complete_sets_summary.html`, selected and checked through `source_index.json` | `figures/Figure_1.png`, `Figure_1.pdf`; a TIFF is also generated during plotting. |
| **Figure 2 — Jianping, Qingyuan and national urea paths** | `python code/plot_figures.py` | `inputs/reference_experiments/figure_export/inputs/T2_plot_panel_1.html` and `T2_plot_panel_2.html`, including each series' price, availability and line-connection fields | `figures/Figure_2.png`, `Figure_2.pdf`; a TIFF is also generated during plotting. |

The plotting command draws both main figures and supplementary Figures S1 and S2 in one run. It reads the archived plotting inputs directly; `results/primary_15_L6.json` is the Table 3 export rather than the Figure 1 read path. `code/frozen_figure_helpers.py` checks carrier identity and validates panel contents before plotting. Independent PNGs are exported at 600 dpi; PDFs contain vector elements.

## Precision checks and report layout

- `node code/precision_extension.mjs` writes the six 9,999-draw checks to `results/precision/`.
- `python code/verify_precision_records.py` compares their count records with the accepted integer counts.
- `python code/mc_precision.py` writes `results/precision/precision_summary_with_MC_error.json` and Table 3's `results/primary_15_L6.json`.
- `python code/verify_episode_point_statistics.py` checks the recorded below-benchmark spells and their update opportunities.
- `python code/build_docx.py` reads `reports/manuscript.md`, embeds the main figures and writes `native/manuscript.docx`.
- `python code/build_supplement.py` reads `reports/supplement.md` and writes `native/supplement.docx`.
- `python code/export_native.py` exports the two rebuilt documents to PDF and page images under `native/render_manuscript_reproduced/` and `native/render_supplement_reproduced/`.

The full `reproduce` command sets the execution order, checks regenerated numerical outputs against the supplied records, and records step logs in `reproduction/`. Targeted commands above are for tracing a specific table or figure. Run those targeted commands only inside a separate working copy, such as `reproduction/workspace/`, because they write the relative output paths shown in the tables. Use the full command for the end-to-end replication with protected reference files.

## Supplement S10 diagnostics

| Item | Command | Input and output |
| --- | --- | --- |
| Monthly variance shares and annual exchange levels | `python code/seasonality_analysis.py` | Reads `inputs/normalized_prices.csv` and the archived county definitions; writes `results/benchmark_checks/seasonality_summary.json`, `seasonality_models.csv` and `seasonality_annual.csv`. The calendar comparison reads `results/alerts/alerts_daily.csv` and writes `seasonality_calendar_comparisons.csv` and `seasonality_calendar_dates.csv`. |
| Product updating, source transitions and national-turn timing | `python code/quotation_timing.py` | Reads the normalized county quotations, expected calendar and `inputs/full_archive/data/national/nbs_prices.csv`; writes `quotation_diagnostics.json` and eight detailed CSV tables under `results/benchmark_checks/`. |
| Supplement S10 Word | `python code/build_docx.py --role supplement_methods` | Reads `reports/supplement_methods.md` and writes `native/supplement_methods.docx`. |

The full `reproduce` entry also computes and validates these diagnostics. Native PDF export includes Supplement S10 alongside the article and original supplement. Run targeted analysis commands in a separate working copy to keep supplied result files unchanged.

## Supplement S11 — supplementary validation

| Check | Command | Inputs | Output |
| --- | --- | --- | --- |
| Symmetric county influence | `node code/county_influence.mjs` | normalized county prices; original L=6 saved paths and historical coefficients | `results/supplementary_validation/county_influence_summary.json` and `.csv` |
| Historical-only screening and later-window comparisons | `python code/supplementary_validation.py` | normalized county prices, original calendar and national quotes limited to the historical fitting window | `results/supplementary_validation/temporal_screen_*` |
| Same-product county peers | `python code/supplementary_validation.py` | original twelve-county observations; all same-source constant runs longer than 36 observations | `results/supplementary_validation/peer_*` |
| S11 document | `python code/build_docx.py --role supplement_validation` | `reports/supplement_validation.md` | `native/supplement_validation.docx`; PDF through the export command |

The full reproduction entry runs both validation programs and compares the saved JSON, CSV and rule files against the recomputed outputs. Discrete quantities and categories are exact; continuous values use the existing numerical tolerance. The original five benchmarks, saved paths and main result files remain unchanged.
