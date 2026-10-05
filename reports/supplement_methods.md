# Supplement S10 Benchmark and quotation diagnostics

This supplement supports the article *Benchmark choice and quotation persistence in county maize–urea price monitoring: Evidence from Liaoning, China*. It explains the historical-window design, reports monthly variation and quotation-update timing, and supplies the resampling details used in the main comparisons. The original Supplements S1–S9 remain in the accompanying supplementary report.

## S10.1 Historical windows and monthly variation

The three-year benchmark uses all complete 2018–2020 observations. Removing 2018 gives the 2019–2020 comparison; removing 2020 gives 2018–2019. The one-year 2020 comparison prioritizes proximity to the later calendar. The month-specific comparison uses twelve county-specific monthly historical means in the same three years. The annual levels below describe the observed reference conditions.

Monthly explanation is measured on y = log Q using three models: month indicators; county and year effects; and county, year and month effects. The raw share is 1 − SSE(month)/TSS. The increment is [SSE(county+year) − SSE(county+year+month)]/TSS. The partial share divides that same difference by SSE(county+year). TSS is centered around the outcome mean. The main county–date panel uses equal weight per valid pair; equal-date weights give each date total weight one. County and year effects absorb between-county and between-year level differences. The month model summarizes within-year calendar association over the three reference years.

Both panels have all 108 dates and no inserted prices. The original twelve counties provide 1,296 pairs and the screened six provide 648. The reduced and full model ranks are 14 and 25 for twelve counties, and 8 and 19 for six. The month rank increment is eleven. Balanced county/year/month cells make the raw share and incremental share equal. The level-ratio and date-mean diagnostics use their own outcome scale and analysis unit.

**Table S10.1. Month-factor explained shares in the complete reference panel.**

| County group | Outcome | County–dates | Raw month share (%) | Partial month share (%) |
| --- | --- | ---: | ---: | ---: |
| Twelve counties | Log ratio | 1,296 | 4.97 | 10.48 |
| Twelve counties | Level ratio | 1,296 | 5.95 | 12.43 |
| Six screened counties | Log ratio | 648 | 5.95 | 13.47 |
| Six screened counties | Level ratio | 648 | 7.38 | 17.03 |

*Note:* Raw shares use total outcome variation; partial shares use the residual variation after county and year effects. For the twelve-county log ratio, the county/year model explains 52.58% of total variation and the full model explains 57.55%. Equal-date weighting gives the same shares in these complete panels. The CSV and JSON give the model sums of squares, coefficient ranks, date-mean diagnostics and full precision.

**Table S10.2. Annual geometric and arithmetic exchange ratios for the twelve counties.**

| Year | Geometric mean Q | Arithmetic mean Q |
| --- | ---: | ---: |
| 2018 | 0.797 | 0.804 |
| 2019 | 0.800 | 0.804 |
| 2020 | 0.997 | 1.010 |

*Note:* Each year includes 432 equally weighted county–date pairs. The geometric mean is exp(mean(log Q)); the arithmetic mean is mean(Q). The 2020 geometric mean is 24.60% above 2019; all twelve county-specific means rise in that comparison. The county-level annual file also shows that eleven counties exceed their 2018 means.

On the common 204 complete dates, the original twelve counties attain the three-year benchmark on 174 dates and the month-specific benchmark on 172. Calendar matching changes classification on eighteen dates: ten leave the attainment set and eight enter it. The net count therefore falls by two. The diagnostic output records these paired classifications by date.

## S10.2 Quotation updating and national-turn dates

Update opportunities are positive adjacent observations on the scheduled calendar within a single source. Decimal equality uses the recorded price strings. Missing observations interrupt a comparison and a numerical run. Descriptive equal-value runs cross a source boundary when the value stays equal; screening runs end at the boundary.

**Table S10.3. Product update counts in the twelve counties.**

| County | Maize updates/opportunities (%) | Urea updates/opportunities (%) |
| --- | --- | --- |
| Sujiatun | 138/313 (44.09%) | 25/313 (7.99%) |
| Faku | 156/313 (49.84%) | 78/313 (24.92%) |
| Zhuanghe | 118/310 (38.06%) | 33/313 (10.54%) |
| Qingyuan | 48/313 (15.34%) | 8/313 (2.56%) |
| Fengcheng | 115/313 (36.74%) | 68/313 (21.73%) |
| Dashiqiao | 59/313 (18.85%) | 48/313 (15.34%) |
| Zhangwu | 186/313 (59.42%) | 26/313 (8.31%) |
| Dengta | 173/313 (55.27%) | 37/313 (11.82%) |
| Dawa | 47/313 (15.02%) | 30/313 (9.58%) |
| Changtu | 96/313 (30.67%) | 55/313 (17.57%) |
| Kaiyuan | 178/313 (56.87%) | 85/313 (27.16%) |
| Jianping | 35/311 (11.25%) | 6/311 (1.93%) |

*Note:* Jianping has 315 scheduled slots and 314 positive observations for each product. One source-boundary comparison and two comparisons adjoining the missing 25 November 2024 observation are excluded from 314 planned transitions, leaving 311. The update file reports all exclusions for every county and product.

Jianping's 1.50-CNY urea value occurs on both 25 January 2024 and 5 February 2024 across source systems 111 and 115. The recorded product specification and unit remain domestic urea and CNY per 500 g; the source-local product codes change from 10147 to 20240610147. Its 94-observation equal-value segment runs from 15 April 2022 to 15 November 2024 and contains 65 observations from the earlier source and 29 from the later source. The missing 25 November 2024 slot separates the later 44-observation segment, from 5 December 2024 to 15 February 2026. The earlier 1.00-CNY segment has 109 observations over 25 April 2018–25 April 2021.

National urea observations are averaged by month without interpolation. The primary rule requires at least two observed dekads, an opposite preceding monthly movement, two consecutive movements in the new direction and a cumulative change of at least 5% from the extremum. Flat months, absent support and calendar gaps interrupt direction sequences. Each confirmation is available on the latest national publication date used to establish it. Only a confirmation available by the local monitoring-report date qualifies. Every county update is paired with the most recent qualifying same-direction turn. The three- and six-month windows use the extremum month, with confirmation-month distances also supplied in the CSV. The first usable national monthly mean is December 2017; the earlier direction history is absent.

**Table S10.4. All six Jianping urea updates under the primary national-turn rule.**

| Local date | Quote change (CNY/500 g) | Turn month / confirmation published | Months from turn | Within 3 / 6 months |
| --- | --- | --- | ---: | --- |
| 2018-04-25 | 0.75 → 1.00 | Unmatched; No eligible turn | — | No / No |
| 2021-05-05 | 1.00 → 1.10 | 2020-09; 2020-12-04 | 8 | No / No |
| 2021-08-15 | 1.10 → 1.40 | 2021-03; 2021-06-04 | 5 | No / Yes |
| 2022-04-15 | 1.40 → 1.50 | 2021-12; 2022-03-04 | 4 | No / Yes |
| 2026-02-25 | 1.50 → 1.20 | 2025-05; 2025-08-04 | 9 | No / No |
| 2026-09-05 | 1.20 → 1.10 | 2026-04; 2026-09-04 | 5 | No / Yes |

*Note:* The unmatched April 2018 update has no assigned distance. No future national confirmation is used. Local dates are the archived monitoring dates; the underlying local transaction and publication dates are not recorded. These rows describe quotation-date alignment.

**Table S10.5. National-turn rule sensitivity for Jianping.**

| Monthly support | Turn amplitude | Earlier matched updates | Within 3 months | Within 6 months |
| --- | --- | ---: | ---: | ---: |
| At least 2 dekads | 5% | 5/6 | 0/6 | 3/6 |
| At least 2 dekads | 10% | 5/6 | 0/6 | 2/6 |
| All 3 dekads | 5% | 5/6 | 0/6 | 1/6 |
| All 3 dekads | 10% | 5/6 | 0/6 | 0/6 |

*Note:* All 499 valid county urea updates are assessed under the same four rules, giving 1,996 matching rows. The complete national candidate list, 107 monthly observations, all county summaries and coverage states accompany the results. The change in matched counts documents the effect of the amplitude and monthly-support rules.

## S10.3 Detailed reference and paired construction

### S10.3.1 Conditional reference

The fixed-benchmark reference holds the observed later aggregate path constant and replaces county deviations with historical residual vectors. On donor date \(s\),

$$
r_{is}=g_{is}-G_s,\qquad
g^{\mathrm{ref}}_{it}=G_t+r_{i,s(t)}. \tag{3}
$$

Non-circular moving blocks resample entire county-date vectors, retaining cross-county co-movement and dependence within each block (Künsch, 1989). Six monitoring periods form the main block length. Paths are generated on all 207 later slots before the original completeness mask is applied. Within a county group, observed and reference statistics use the same attainment dates. Thus the comparison asks whether historical county deviations produce a similar below-benchmark share along the actual aggregate trajectory.

Each configuration has 1,999 draws. The reference envelope is the two-sided 90% percentile interval, from the fifth to the ninety-fifth percentile. The one-sided upper-tail estimate is \(\widehat p=(K+1)/(R+1)\), where \(K\) counts reference statistics at least as large as the observation and \(R\) counts valid draws. Ties are included.

This reference is conditional on an estimated historical threshold. It separates the county distribution from the realized aggregate path, but leaves benchmark-estimation variation for a second experiment. The distinction matters when a short historical window contains different price levels from a longer window. A small conditional-reference tail estimate can coexist with a paired interval that includes zero because the two calculations vary different components of the comparison.

### S10.3.2 Paired benchmark re-estimation

For each outer repetition, historical county-date vectors are resampled and the county benchmark \(b_i^*\) is re-estimated. Later county positions, the aggregate path and the attainment set are then recalculated. Historical residual candidates are recomputed relative to \(b_i^*\) and centered across counties on each donor date. An independent inner stream supplies one residual path for that outer draw. Both statistics use the same newly calculated attainment set.

Let \(O^*\) and \(K_{\mathrm{ref}}^*\) denote the observed and reference below-benchmark county–date counts in the same repetition, and \(T^*\) its number of attainment dates. They differ from the fixed-reference tail count \(K\), which counts draws. The paired difference is

$$
D^*=\overline H^{\,\mathrm{obs},*}-\overline H^{\,\mathrm{ref},*}
=\frac{O^*-K_{\mathrm{ref}}^*}{NT^*}. \tag{4}
$$

We report the equally weighted mean difference, a two-sided 95% percentile interval and the proportion of differences above zero. Empty attainment sets have unavailable reference statistics. The residuals are centered across counties on each donor date. Each outer draw has one independent residual path, so the difference distribution combines benchmark-estimation variation and residual-path variation; its positive fraction is a distribution summary rather than a p value.

One inner path per outer draw means the paired distribution combines benchmark-estimation variability and residual-path randomness. Annual outer draws use non-circular blocks within the selected window. The month-specific benchmark matches the starting month and the fifth/fifteenth/twenty-fifth reporting slot, keeps seasonal progression within complete blocks, and fills the historical target calendar; its inner paths use the same seasonal alignment on the later calendar. Outer and inner random streams are independent. Cohorts share date indices within a benchmark and block length while recalculating their own positions and denominators.

Supplement S2 reports all five benchmarks for the original counties, the eleven counties excluding Jianping (the eleven-county group), and the ten counties excluding both low-update counties, at block lengths three, six and twelve. Supplement S7d reports the groups passing the full screen at six-period blocks. Table 3 uses 1,999 draws throughout. Historical sample sizes and resampling support are documented in the technical note.

### S10.3.3 Resampling precision

We distinguish Monte Carlo estimation error from the spread of the reference and paired distributions. We report Monte Carlo standard errors for interior tail estimates and exact binomial bounds when K=0 or K=R. The smallest plus-one estimate is 1/(R+1). Percentile limits use linear interpolation, and discrete outcomes can place a limit exactly at zero. Supplement S9a and S9c give the counts, standard errors and binomial intervals; the technical note gives their formulas.

Six comparisons were selected before extending the resampling analysis: the 2018–2020 benchmark for the original twelve counties, the eleven counties excluding Jianping and the six screened counties; the 2020 benchmark for the ten- and six-county groups; and the month-specific benchmark for the eleven-county group. The six comparisons were extended to 9,999 draws using the same random streams. We report these precision checks separately from the 1,999-draw main analysis in Supplement S9a.



### S10.3.4 Definitions and boundary precision for the main comparison table

*Note:* H is a percent; D and its interval are percentage points. The reference envelopes, reported in Supplement S2 and S7d, are two-sided 90% percentile intervals; paired intervals are two-sided 95%. Fixed-reference p is a one-sided upper-tail Monte Carlo estimate with ties. Boundary entries are reported as ≤0.0005 † for a zero tail count and ≥0.9995 † for a complete tail count; their raw plus-one estimates are 0.0005 and 1.0000, respectively. MCSE is replaced by a one-sided 95% binomial bound. With 1,999 draws, a zero tail gives an upper bound of about 0.00150 for the underlying tail probability, and a complete tail gives a lower bound of about 0.99850. The tail-probability resolution is 0.0005. D>0 reports the share of positive paired draws. Supplement S10 explains the tail-count bounds and their relation to the paired interval.

The positive fraction is a summary of the paired difference distribution. The fixed-reference upper-tail estimate and the positive paired fraction summarize different comparisons: the former counts reference statistics at least as large as the observed statistic; the latter counts resampled observed-minus-reference differences above zero.

## S10.4 Reproduction files

The month-factor program is code/seasonality_analysis.py. It reads the unchanged normalized county prices and historical county definitions and writes seasonality_summary.json, seasonality_models.csv and seasonality_annual.csv. It also compares the supplied alert classifications in seasonality_calendar_comparisons.csv and seasonality_calendar_dates.csv. The quotation program is code/quotation_timing.py. It reads the county calendar, original decimal quotations and national urea reports and writes quotation_diagnostics.json and eight supporting CSV tables. All these result files are in results/benchmark_checks.

The project's reproduce entry runs both programs in its isolated working copy, compares their outputs with the supplied records and rebuilds this note together with the article and original supplement. Program and data paths, source records and complete precision values are supplied in the project documentation. The original scientific inputs and the earlier benchmark, alert and screening results are unchanged.


## S10.5 Comparison design and resampling details

### S10.5.1 Conditional reference along the observed aggregate path

We hold the observed later aggregate path constant and replace county deviations with historical residual vectors. The residual construction is given in equation (3) above.

Moving blocks sample whole county-date vectors, keeping cross-county co-movement and short-run dependence together (Künsch, 1989). The main comparison uses six-period blocks and 1,999 draws. Observed and reference incidence use the same county group, aggregate path and attainment dates. We report a two-sided 90% reference interval and a one-sided upper-tail estimate with ties included. Supplement S10 gives the resampling calendar, tail-count formula and computational details.

This comparison asks whether historical county deviations reproduce the observed below-benchmark share along the actual aggregate trajectory. It holds the estimated historical threshold fixed. The paired comparison below additionally varies that threshold.

### S10.5.2 Paired benchmark re-estimation

We resample historical county-date vectors, re-estimate each county's benchmark and recalculate the later aggregate path and attainment dates. Historical county residuals are recomputed for that draw. A separate residual path supplies a reference comparison on the same recalculated attainment set.

Let \(O^*\) and \(K_{\mathrm{ref}}^*\) denote the observed and reference below-benchmark county–date counts, and \(T^*\) the attainment-date count. The paired difference is given in equation (4) above.

We report the mean difference, a two-sided 95% percentile interval and the share of draws with a positive difference. Each draw combines historical-mean variation with a residual-path comparison. Month-specific benchmarks use seasonally aligned blocks. The county groups share resampled date indices and use their own recalculated aggregate and incidence. Supplement S2 reports the original, eleven- and ten-county groups at three block lengths; Supplement S7d reports the fully screened groups. Supplement S10 supplies the full construction, including the treatment of empty attainment sets.

### S10.5.3 Resampling precision

Table 3 uses 1,999 draws for every comparison. Six selected comparisons were extended to 9,999 draws using the same random streams; they are reported separately in Supplement S9a. Monte Carlo standard errors and binomial boundary intervals describe the numerical precision of tail estimates. Their counts, formulas and quantile conventions appear in Supplements S9a, S9c and S10.

## S8 figure documentation addendum

This addendum supplies the full figure descriptions and series-continuity details accompanying Supplements S8a–S8d. The original Supplement S8 remains in the accompanying S1–S9 report.

### Figure 1: full caption and panel definitions

Figure 1. Benchmark dependence for Full12, U10 and S6. The categorical panels report aggregate attainment on the same 204 complete dates, conditional mean H with the fixed-reference mean and its two-sided 90% interval, the one-sided fixed-reference tail estimate with Monte Carlo uncertainty, and paired mean D with its 95% interval. Points are grouped by county membership; different benchmarks are not connected by lines. All panels use six-period blocks and 1,999 draws. H is a percent and D is in percentage points. Data sources: the five-benchmark results in Table 3 and Supplement S2 and S7d.

### Figure 2: full caption and series continuity

Figure 2. Urea quotation paths for Jianping, Qingyuan and the national circulation-market survey. Panels (a) and (b) compare the focal county with the median of the other eleven counties; panel (c) shows national urea. Each series is expressed as log price minus its own mean over the three January 2018 observations. County lines break at their source boundary and unavailable scheduled observations. Each median line follows the availability and source continuity of its own eleven-county comparison group; Qingyuan's comparison is unavailable on 25 November 2024. National lines break at their own unavailable periods. Legends sit outside the data area. Annotations distinguish Jianping's 94-observation segment and separate 44-observation segment. Data sources: the archived county and national price observations in Supplement S8a–S8b.

County quotations are expressed in CNY per 500 g. Multiplication by two converts them to CNY per kilogram and preserves their ratio. Equality and updating are determined from the original decimal values, rather than rounded logarithms. Screening runs stop at the source change between 25 January and 5 February 2024. Descriptive numerical-persistence segments continue across that boundary when consecutive scheduled positive values remain equal. Zeros and missing planned observations end a continuous observed segment; equal values separated by a gap receive a separate observed-span record.

A later urea level of 1.50 persists for 94 observations from 15 April 2022 to 15 November 2024, crossing the archive source boundary. The unavailable 25 November observation ends that sequence. Another 44 equal observations run from 5 December 2024 to 15 February 2026. The 138 equal quotations form two consecutive segments of 94 and 44 observations, separated by the missing November 2024 slot. During the first segment, the national urea quotation falls from 2,885.2 to 1,867.2 CNY per tonne, a decline of 35.28%; the other-eleven-county endpoint median falls from 1.60 to 1.00 CNY per 500 g.

Qingyuan's longest urea segment contains 80 observations at 1.10 from 5 January 2018 to 15 March 2020. Its later 1.60 segment contains 75 observations from 25 March 2022 to 15 April 2024 and crosses the source boundary without a county gap. The corresponding other-eleven-county medians are 1.55 and 1.25 at its endpoints. Qingyuan's comparison group includes Jianping, while Jianping's group includes Qingyuan; their comparison lines have different missing-date masks. Figure 2 follows each observed series on its own calendar.
