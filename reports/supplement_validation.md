# Supplement S11: County influence, historical screening and same-product peers

## S11.1 Design

We extend the benchmark and quotation-persistence analysis with three supplementary checks. First, every county is deleted once under every historical benchmark. These sixty comparisons use the same 204 complete monitoring dates, six-observation blocks and 1,999 saved sampling paths as the original comparison. The five twelve-county controls and five Jianping-deletion controls match the existing results. The paired distribution jointly varies historical means and residual reference paths. We classify each interval from its unrounded endpoints.

Second, we apply the existing screen using only county observations from 5 January 2018 to 25 December 2020 and national observations available by that end date. The product update-rate threshold is one-third of the historical twelve-county median. A same-source constant run is flagged when it exceeds 36 observations and its observed national amplitude exceeds 20%. Partial national coverage with subthreshold movement is classified as unresolved. County classifications are fixed before describing the 2021–2023 and January 2024–September 2026 windows.

The temporal alert comparison uses the 2018–2020 county mean log-ratio benchmark. Both county groups use the original twelve-county common complete-date mask. The aggregate condition runs across the whole post-2020 scheduled calendar: a missing date resets it, an unchanged source-boundary condition continues it, and the third qualifying observation starts the alert. Window totals count the dates falling inside each validation period. Product updating uses valid same-source adjacent observations within each period; pooled rates divide total changes by total eligible transitions.

Third, for all same-source constant runs longer than 36 observations in either product, we compare the focal quotation with the same product, specification and unit in the other eleven original counties. The target county is excluded. The median uses only dates with all eleven peers observed and positive. Coverage is reported separately. Peer update counts use adjacent same-source observations within the focal run.

## S11.2 Symmetric county influence

The sixty comparisons produce 53 strictly positive intervals and seven intervals containing zero. No interval is strictly negative. Under the 2018–2020 benchmark, deletion of Qingyuan, Dawa, Changtu or Jianping makes the interval include zero. Under 2019–2020, 2018–2019 and the month-specific benchmark, only Jianping's deletion does so. Under 2020, all twelve deletions leave a strictly positive interval.

Benchmark choice continues to determine alert intensity across these deletions. The annual 2020 benchmark produces 118–134 aggregate alert dates; 2018–2019 produces zero to two. This comparison reports every county's influence under the same calendar and sampling design.

**Table S11.1. Results across the twelve deletions under each benchmark.**

| Benchmark | Positive / include zero | Attainment range (%) | Aggregate alert dates |
| --- | --- | --- | --- |
| 2018–2020 | 8 / 4 | 82.84–89.71 | 12–25 |
| 2019–2020 | 11 / 1 | 68.63–79.41 | 32–47 |
| 2020 | 12 / 0 | 31.37–37.25 | 118–134 |
| 2018–2019 | 11 / 1 | 97.06–100.00 | 0–2 |
| Same month, 2018–2020 | 11 / 1 | 82.84–88.24 | 15–25 |

*Note: There are twelve deletion comparisons per benchmark. Attainment uses 204 common complete dates. The complete machine-readable results also include both county-share alert rules.*

## S11.3 Historical selection and later observations

Historical information alone flags Sujiatun, Qingyuan, Dashiqiao, Dawa and Jianping. Faku is unresolved because national coverage in its relevant historical run is incomplete; the remaining six counties are not flagged. The later comparison fixes the seven counties without a confirmed historical flag, including Faku, alongside all twelve counties.

The five historically flagged counties update less frequently than the other seven in both subsequent windows and for both products. Urea updating is 13.46% versus 25.23% in 2021–2023 and 6.42% versus 18.11% in January 2024–September 2026. Maize updating is 27.85% versus 56.57% and 23.19% versus 51.40%, respectively. The historical classification therefore identifies reporting patterns that persist into later observations.

**Table S11.2. Historical-only county classification.**

| County | Historical status | Later group |
| --- | --- | --- |
| Sujiatun | flagged | Flagged five |
| Faku | unresolved | Seven without confirmed flag |
| Zhuanghe | not_flagged | Seven without confirmed flag |
| Qingyuan | flagged | Flagged five |
| Fengcheng | not_flagged | Seven without confirmed flag |
| Dashiqiao | flagged | Flagged five |
| Zhangwu | not_flagged | Seven without confirmed flag |
| Dengta | not_flagged | Seven without confirmed flag |
| Dawa | flagged | Flagged five |
| Changtu | not_flagged | Seven without confirmed flag |
| Kaiyuan | not_flagged | Seven without confirmed flag |
| Jianping | flagged | Flagged five |

*Note: The seven-county comparison includes the unresolved Faku record. The membership is fixed using historical information.*

**Table S11.3. Update counts and pooled rates by fixed historical membership.**

| Period | Product | Flagged five | Other seven |
| --- | --- | --- | --- |
| 2018–2020 | Maize | 61/535 (11.40%) | 243/749 (32.44%) |
| 2018–2020 | Urea | 14/535 (2.62%) | 70/749 (9.35%) |
| 2021–2023 | Maize | 149/535 (27.85%) | 422/746 (56.57%) |
| 2021–2023 | Urea | 72/535 (13.46%) | 189/749 (25.23%) |
| 2024–September 2026 | Maize | 112/483 (23.19%) | 349/679 (51.40%) |
| 2024–September 2026 | Urea | 31/483 (6.42%) | 123/679 (18.11%) |

*Note: Each cell gives changes / eligible same-source transitions and the pooled percentage. Product and county missingness determine the denominators. County median rates are supplied in the result files.*

**Table S11.4. Later-window classifications under the 2018–2020 benchmark.**

| Period | County group | Attainment dates | Aggregate alert dates | Half-share alerts |
| --- | --- | --- | --- | --- |
| 2021–2023 | All twelve | 89/106 | 13/106 | 18 |
| 2021–2023 | Seven without confirmed flag | 88/106 | 12/106 | 20 |
| 2024–September 2026 | All twelve | 85/98 | 6/98 | 13 |
| 2024–September 2026 | Seven without confirmed flag | 88/98 | 4/98 | 11 |

*Note: The two validation periods have 106 and 98 common complete dates. Aggregate alerts require three consecutive qualifying scheduled observations. Half-share alerts require at least half of the group below its county historical benchmark.*

## S11.4 Same-product county peers

All twenty same-source constant runs longer than 36 observations coincide with at least one updating peer county. Three runs coincide with a fixed eleven-county median amplitude above 20%: Qingyuan urea from 25 March 2022 to 25 January 2024 (30.77%), Jianping urea from 15 April 2022 to 25 January 2024 (30.77%), and Dawa urea from 5 February 2024 to 15 March 2025 (25.71%). These same-product comparisons document market movement elsewhere in the provincial archive during unchanged focal quotations.

**Table S11.5. All long unchanged runs and their eleven-county same-product reference.**

| County | Product | Constant-run dates | Observations | Median amplitude (%) | Updating peers | Complete-date coverage (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Sujiatun | Maize | 2018-02-15 to 2019-09-25 | 59 | 13.41 | 9 | 100.00 |
| Sujiatun | Urea | 2018-01-05 to 2020-04-15 | 83 | 15.79 | 11 | 100.00 |
| Faku | Urea | 2018-04-25 to 2019-08-15 | 48 | 6.80 | 8 | 100.00 |
| Zhuanghe | Urea | 2019-07-25 to 2020-07-25 | 37 | 10.00 | 9 | 100.00 |
| Qingyuan | Maize | 2024-10-05 to 2026-03-05 | 52 | 15.15 | 11 | 98.08 |
| Qingyuan | Urea | 2018-01-05 to 2020-03-15 | 80 | 15.79 | 10 | 100.00 |
| Qingyuan | Urea | 2020-03-25 to 2021-03-25 | 37 | 15.00 | 10 | 100.00 |
| Qingyuan | Urea | 2022-03-25 to 2024-01-25 | 67 | 30.77 | 11 | 100.00 |
| Qingyuan | Urea | 2025-03-15 to 2026-09-25 | 56 | 10.00 | 10 | 100.00 |
| Dashiqiao | Maize | 2018-01-05 to 2020-02-25 | 78 | 16.25 | 10 | 100.00 |
| Dashiqiao | Urea | 2019-05-05 to 2021-02-25 | 66 | 15.00 | 10 | 100.00 |
| Zhangwu | Urea | 2025-02-25 to 2026-09-25 | 58 | 10.00 | 11 | 100.00 |
| Dawa | Maize | 2018-01-05 to 2020-04-05 | 82 | 16.25 | 11 | 100.00 |
| Dawa | Urea | 2024-02-05 to 2025-03-15 | 41 | 25.71 | 10 | 97.56 |
| Jianping | Maize | 2018-05-05 to 2019-08-15 | 47 | 7.32 | 8 | 100.00 |
| Jianping | Maize | 2022-12-05 to 2023-12-15 | 38 | 10.94 | 11 | 100.00 |
| Jianping | Maize | 2025-03-15 to 2026-09-25 | 56 | 9.52 | 11 | 100.00 |
| Jianping | Urea | 2018-04-25 to 2021-04-25 | 109 | 15.00 | 11 | 100.00 |
| Jianping | Urea | 2022-04-15 to 2024-01-25 | 65 | 30.77 | 10 | 100.00 |
| Jianping | Urea | 2024-12-05 to 2026-02-15 | 44 | 20.00 | 11 | 100.00 |

*Note: Amplitude is maximum divided by minimum minus one on dates with all eleven fixed peers observed. Updating peers count counties with at least one eligible same-source update inside the focal run. Individual quotation-cell coverage and the daily median series are supplied in peer_runs.csv and peer_daily.csv.*

## S11.5 Complete county influence results

The following tables report all sixty deletions and the five twelve-county controls. Paired differences and intervals are in percentage points. The original five benchmarks and the original sampling paths are used throughout. Tail estimates at the sampling boundary are shown with an inequality.

**Table S11.6. 2018–2020: each county deletion and the twelve-county control.**

| Excluded county | Attainment (%) | Paired mean (pp) | Paired 95% interval (pp) | Fixed tail |
| --- | --- | --- | --- | --- |
| All twelve | 85.29 | 2.66 | [0.20, 5.12] | ≤0.0005 |
| Sujiatun | 85.78 | 2.62 | [0.21, 5.09] | 0.002 |
| Faku | 84.80 | 3.67 | [1.08, 6.26] | ≤0.0005 |
| Zhuanghe | 85.78 | 2.85 | [0.34, 5.43] | ≤0.0005 |
| Qingyuan | 86.76 | 2.04 | [-0.29, 4.37] | 0.014 |
| Fengcheng | 83.33 | 3.46 | [0.82, 6.06] | ≤0.0005 |
| Dashiqiao | 83.33 | 3.15 | [0.76, 5.70] | ≤0.0005 |
| Zhangwu | 84.80 | 3.04 | [0.48, 5.62] | ≤0.0005 |
| Dengta | 82.84 | 3.37 | [0.69, 6.03] | ≤0.0005 |
| Dawa | 82.84 | 2.00 | [-0.71, 4.68] | 0.007 |
| Changtu | 86.27 | 2.59 | [-0.05, 5.27] | ≤0.0005 |
| Kaiyuan | 84.80 | 2.86 | [0.34, 5.47] | ≤0.0005 |
| Jianping | 89.71 | 0.19 | [-2.25, 2.70] | 0.093 |

*Note: Interval classifications use full-precision endpoints. The first row is the original twelve-county comparison, followed by all twelve single-county deletions.*

**Table S11.7. 2019–2020: each county deletion and the twelve-county control.**

| Excluded county | Attainment (%) | Paired mean (pp) | Paired 95% interval (pp) | Fixed tail |
| --- | --- | --- | --- | --- |
| All twelve | 75.00 | 4.61 | [1.41, 8.77] | ≤0.0005 |
| Sujiatun | 74.02 | 4.72 | [1.64, 9.00] | 0.001 |
| Faku | 73.53 | 6.04 | [2.62, 10.63] | ≤0.0005 |
| Zhuanghe | 76.96 | 4.60 | [1.59, 7.98] | 0.001 |
| Qingyuan | 75.00 | 4.40 | [1.19, 9.17] | ≤0.0005 |
| Fengcheng | 76.47 | 4.96 | [1.83, 8.92] | ≤0.0005 |
| Dashiqiao | 69.61 | 3.84 | [0.77, 7.87] | 0.001 |
| Zhangwu | 79.41 | 5.10 | [1.81, 8.56] | ≤0.0005 |
| Dengta | 73.04 | 4.75 | [1.41, 9.09] | ≤0.0005 |
| Dawa | 68.63 | 3.47 | [0.38, 7.25] | 0.002 |
| Changtu | 74.02 | 4.79 | [1.12, 9.63] | ≤0.0005 |
| Kaiyuan | 74.51 | 5.13 | [1.68, 9.85] | ≤0.0005 |
| Jianping | 77.45 | 3.09 | [-0.43, 8.09] | 0.003 |

*Note: Interval classifications use full-precision endpoints. The first row is the original twelve-county comparison, followed by all twelve single-county deletions.*

**Table S11.8. 2020: each county deletion and the twelve-county control.**

| Excluded county | Attainment (%) | Paired mean (pp) | Paired 95% interval (pp) | Fixed tail |
| --- | --- | --- | --- | --- |
| All twelve | 34.31 | 8.58 | [3.10, 14.06] | ≤0.0005 |
| Sujiatun | 32.35 | 9.04 | [3.56, 14.94] | ≤0.0005 |
| Faku | 31.86 | 9.93 | [3.86, 15.78] | ≤0.0005 |
| Zhuanghe | 35.78 | 8.91 | [3.87, 13.90] | ≤0.0005 |
| Qingyuan | 37.25 | 9.17 | [2.86, 14.98] | ≤0.0005 |
| Fengcheng | 34.80 | 8.34 | [2.76, 14.30] | ≤0.0005 |
| Dashiqiao | 31.86 | 8.55 | [3.90, 13.73] | ≤0.0005 |
| Zhangwu | 35.29 | 7.03 | [1.37, 11.83] | ≤0.0005 |
| Dengta | 33.33 | 9.44 | [4.07, 15.07] | ≤0.0005 |
| Dawa | 31.37 | 6.30 | [0.77, 12.71] | 0.011 |
| Changtu | 33.82 | 8.92 | [3.64, 15.15] | ≤0.0005 |
| Kaiyuan | 34.80 | 9.19 | [3.33, 14.81] | ≤0.0005 |
| Jianping | 35.78 | 8.90 | [2.11, 13.70] | ≤0.0005 |

*Note: Interval classifications use full-precision endpoints. The first row is the original twelve-county comparison, followed by all twelve single-county deletions.*

**Table S11.9. 2018–2019: each county deletion and the twelve-county control.**

| Excluded county | Attainment (%) | Paired mean (pp) | Paired 95% interval (pp) | Fixed tail |
| --- | --- | --- | --- | --- |
| All twelve | 99.02 | 4.79 | [2.61, 7.15] | ≤0.0005 |
| Sujiatun | 98.53 | 4.90 | [2.48, 7.40] | ≤0.0005 |
| Faku | 100.00 | 5.63 | [3.37, 8.02] | ≤0.0005 |
| Zhuanghe | 98.53 | 5.53 | [3.17, 7.97] | ≤0.0005 |
| Qingyuan | 98.53 | 4.80 | [2.57, 7.19] | ≤0.0005 |
| Fengcheng | 99.51 | 5.45 | [3.24, 7.89] | ≤0.0005 |
| Dashiqiao | 100.00 | 5.05 | [2.64, 7.62] | ≤0.0005 |
| Zhangwu | 100.00 | 4.65 | [2.24, 7.13] | ≤0.0005 |
| Dengta | 97.06 | 6.12 | [4.33, 7.80] | ≤0.0005 |
| Dawa | 98.53 | 4.61 | [2.21, 7.35] | ≤0.0005 |
| Changtu | 98.53 | 5.22 | [2.95, 7.44] | ≤0.0005 |
| Kaiyuan | 100.00 | 5.25 | [2.86, 7.71] | ≤0.0005 |
| Jianping | 100.00 | -0.02 | [-2.13, 2.14] | 0.822 |

*Note: Interval classifications use full-precision endpoints. The first row is the original twelve-county comparison, followed by all twelve single-county deletions.*

**Table S11.10. Same month, 2018–2020: each county deletion and the twelve-county control.**

| Excluded county | Attainment (%) | Paired mean (pp) | Paired 95% interval (pp) | Fixed tail |
| --- | --- | --- | --- | --- |
| All twelve | 84.31 | 4.40 | [2.08, 6.89] | ≤0.0005 |
| Sujiatun | 85.29 | 4.55 | [2.25, 7.10] | ≤0.0005 |
| Faku | 86.27 | 4.69 | [2.23, 7.31] | ≤0.0005 |
| Zhuanghe | 84.80 | 4.63 | [2.26, 7.11] | ≤0.0005 |
| Qingyuan | 83.82 | 3.98 | [1.67, 6.60] | ≤0.0005 |
| Fengcheng | 84.31 | 5.00 | [2.60, 7.44] | ≤0.0005 |
| Dashiqiao | 83.82 | 4.81 | [2.47, 7.17] | ≤0.0005 |
| Zhangwu | 88.24 | 4.74 | [2.25, 7.30] | ≤0.0005 |
| Dengta | 82.84 | 5.09 | [2.49, 7.71] | ≤0.0005 |
| Dawa | 82.84 | 3.76 | [1.21, 6.47] | ≤0.0005 |
| Changtu | 84.31 | 4.44 | [2.08, 7.14] | ≤0.0005 |
| Kaiyuan | 85.78 | 4.54 | [2.05, 7.24] | ≤0.0005 |
| Jianping | 87.25 | 2.31 | [0.00, 5.01] | ≤0.0005 |

*Note: Interval classifications use full-precision endpoints. The first row is the original twelve-county comparison, followed by all twelve single-county deletions.*

## S11.6 Reproduction

The complete project entry runs the supplementary checks and compares their outputs with the supplied reference results. County influence is calculated by `code/county_influence.mjs`; historical screening and same-product peers are calculated by `code/supplementary_validation.py`. JSON and CSV results are in `results/supplementary_validation/`. The document is built from `reports/supplement_validation.md`. See the project replication map for command and file details.
