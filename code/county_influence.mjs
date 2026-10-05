import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const R = 1999, L = 6, TOL = 1e-12;
export const COUNTY_IDS = ['210111000000','210124000000','210283000000','210423000000','210682000000','210882000000','210922000000','211081000000','211121000000','211224000000','211282000000','211322000000'];
const COUNTY_NAMES = ['Sujiatun','Faku','Zhuanghe','Qingyuan','Fengcheng','Dashiqiao','Zhangwu','Dengta','Dawa','Changtu','Kaiyuan','Jianping'];
const BENCHMARKS = {B0:'2018–2020', B1:'2019–2020', B2:'2020', B3:'2018–2019', B4:'Same month, 2018–2020'};
const INPUT_HASH = 'f5536401160dc415b33ee7934081484a208aaefc1fa7fd7c6eff6a8b822a906b';
const COUNT_FIELDS = ['condition_count','observed_count','reference_count','observed_any_count','reference_any_count','fixed_reference_count','fixed_reference_any_count'];
const sha = b => crypto.createHash('sha256').update(b).digest('hex');

// Symmetric design: every county is excluded once under every benchmark.
// All runs use the original complete-date mask and the same saved L6 paths.
// Neither the screening rule nor the original benchmark comparison is changed.
export function countyColumns(excluded = null) {
  if (excluded !== null && !COUNTY_IDS.includes(excluded)) throw new RangeError('Excluded county must belong to the twelve-county study panel');
  return COUNTY_IDS.map((_, i) => i).filter(i => COUNTY_IDS[i] !== excluded);
}

export function summarizeAlerts(observations, N) {
  let belowRun = 0;
  const previous = [false,false,false], output = Array.from({length:3}, () => ({dates:[], episodes:0}));
  for (const r of observations) {
    belowRun = r.valid && r.G < -TOL ? belowRun + 1 : 0;
    const trigger = [r.valid && belowRun >= 3, r.valid && 3*r.k >= N, r.valid && 2*r.k >= N];
    for (let i=0;i<3;i++) {
      if (trigger[i]) output[i].dates.push(r.date);
      if (trigger[i] && !previous[i]) output[i].episodes++;
      previous[i] = trigger[i];
    }
  }
  // Missing scheduled observations reset consecutive runs and all episodes.
  // Source boundaries alone do not reset an episode while its trigger holds.
  return output.map((x,i) => ({rule:['aggregate_three_dates','H_ge_third','H_ge_half'][i],
    required_count:i===0?null:Math.ceil(N/(i===1?3:2)), trigger_dates:x.dates.length,
    trigger_percent:100*x.dates.length/204, episodes:x.episodes,
    first:x.dates[0]??null, last:x.dates.at(-1)??null, dates:x.dates}));
}

export async function run(outputDir = path.join(ROOT,'results/supplementary_validation')) {
  const read = p => fs.readFile(path.join(ROOT,'inputs/reference_experiments',p),'utf8');
  const inert = async p => {
    const m = (await read(p)).match(/<script\b[^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/);
    if (!m) throw Error('Missing archived JSON: '+p);
    return JSON.parse(m[1]);
  };
  const core = await read('T4b_source/screened_reference_core.js');
  const text = await read('T1_source/text_csv.js');
  const guard = await read('T1_source/record_schema.js');
  const s = new Function(core+text+guard+'\nreturn {panelFromCsv,parseCsv,MAIN12,estimateB,baselineIndices,rowB,postStats,residuals,referenceStats,groupRecord,summarizeRetained,decodeReplicatePart};')();
  if (JSON.stringify(s.MAIN12)!==JSON.stringify(COUNTY_IDS)) throw Error('County order mismatch');
  const input = await fs.readFile(path.join(ROOT,'inputs/normalized_prices.csv'));
  if (sha(input)!==INPUT_HASH) throw Error('Normalized input hash mismatch');
  const P = s.panelFromCsv(input.toString('utf8'),s.parseCsv);
  const primary = JSON.parse(await fs.readFile(path.join(ROOT,'results/primary_15_L6.json'),'utf8'));
  const expected = (await inert('figure_export/inputs/T1_summary.html')).summary;
  const catalogue = JSON.parse(await read('T1_source/actual_records_catalogue.json'));
  const summary = [], checks = [], pathHashes = {};

  function compare(actual, prior, fields) {
    for (const key of fields) {
      const a = actual[key], b = prior[key];
      if (Array.isArray(b)) {
        if (a.length!==b.length || a.some((v,i)=>v===null?b[i]!==null:Math.abs(v-b[i])>1e-12)) throw Error('Control interval mismatch: '+key);
      } else if (typeof b==='number' && (!Number.isFinite(a)||Math.abs(a-b)>1e-12)) throw Error('Control mismatch: '+key);
      else if (b===null && a!==null) throw Error('Control null mismatch: '+key);
      else if (typeof b==='string' && a!==b) throw Error('Control label mismatch: '+key);
    }
  }

  for (const b of Object.keys(BENCHMARKS)) {
    const packet = await inert('T1_indices/T1_'+b+'_L6_indices_rep1_1999.html');
    const bytes = Buffer.from(packet.base64,'base64'), m = packet.metadata;
    if (m.L!==L || m.group_repetitions!==R || bytes.length!==R*m.record_width || sha(bytes)!==m.whole_group_sha256) throw Error('Saved path identity: '+b);
    const I = {...m,bytes,R}; pathHashes[b] = sha(bytes);
    const saved = [];
    for (const f of catalogue.files.filter(f=>f.metadata.benchmark===b && f.metadata.L===L).sort((a,z)=>a.metadata.rep_start-z.metadata.rep_start)) {
      saved.push(...s.decodeReplicatePart(await inert('T1_records/'+f.title+'.html'),v=>new Uint8Array(Buffer.from(v,'base64'))));
    }
    if (saved.length!==R*3) throw Error('Saved control record count: '+b);
    const savedBy = new Map(saved.map(r=>[r.rep+'|'+r.cohort,r]));
    const fixedB = s.estimateB(P,b,s.baselineIndices(b));
    const prepared = [null,...COUNTY_IDS].map(excluded=>{
      const cols = countyColumns(excluded), obs = s.postStats(P,b,fixedB,cols);
      return {excluded, cols, obs, residual:s.residuals(P,b,fixedB,cols), rows:[]};
    });
    let countComparisons = 0;
    for (let rep=0;rep<R;rep++) {
      const paths = s.groupRecord(I,rep), bStar = savedBy.get((rep+1)+'|all12').bStar;
      // Archived coefficients accompany the archived paths, preserving existing
      // count comparisons at decimal-equality boundaries across runtimes.
      for (const q of prepared) {
        const obs = s.postStats(P,b,bStar,q.cols), ref = s.referenceStats(obs,s.residuals(P,b,bStar,q.cols),paths.inner);
        const fixed = s.referenceStats(q.obs,q.residual,paths.fixed);
        const r = {rep:rep+1,counties:q.cols.length, condition_count:obs.condition_count,
          observed_count:obs.low_count, reference_count:ref.low_count, observed_any_count:obs.any_count,
          reference_any_count:ref.any_count, fixed_reference_count:fixed.low_count, fixed_reference_any_count:fixed.any_count};
        if (q.excluded===null || q.excluded==='211322000000') {
          const name = q.excluded===null?'all12':'without_Jianping11';
          const prior = savedBy.get(r.rep+'|'+name);
          for (const field of COUNT_FIELDS) {if (r[field]!==prior[field]) throw Error('Saved count mismatch: '+b+'/'+name+'/'+r.rep+'/'+field); countComparisons++;}
        }
        q.rows.push(r);
      }
    }
    for (const q of prepared) {
      const n = q.cols.length, result = s.summarizeRetained(I,q.rows,q.obs,n);
      const lo = result.paired_D_95[0], hi = result.paired_D_95[1];
      const observations = Array.from({length:207},(_,pt)=>{
        const t = 108+pt, valid = P.mask[t], base = s.rowB(P,b,fixedB,t);
        const g = valid?q.cols.map(j=>P.x[t][j]-base[j]):null;
        return {date:P.dates[t], valid, G:valid?g.reduce((a,z)=>a+z,0)/n:null, k:valid?g.filter(v=>v<-TOL).length:null};
      });
      const fixedTailCount = q.rows.filter(r=>r.fixed_reference_count!==null && r.fixed_reference_count>=q.obs.low_count).length;
      const pairedRows = q.rows.filter(r=>r.condition_count>0 && r.reference_count!==null);
      const positiveCount = pairedRows.filter(r=>r.observed_count>r.reference_count).length;
      const zeroCount = pairedRows.filter(r=>r.observed_count===r.reference_count).length;
      const row = {...result, fixed_tail_count:fixedTailCount, positive_count:positiveCount, zero_count:zeroCount,
        negative_count:pairedRows.length-positiveCount-zeroCount,
        benchmark_label:BENCHMARKS[b], excluded_county_id:q.excluded,
        excluded_county:q.excluded===null?'None':COUNTY_NAMES[COUNTY_IDS.indexOf(q.excluded)],
        retained_county_ids:q.cols.map(j=>COUNTY_IDS[j]), complete_monitoring_dates:204,
        observed_attainment_fraction:q.obs.condition_count/204,
        observed_attainment_percent:100*q.obs.condition_count/204,
        interval_class:lo===null?'no_valid_pairs':lo>0?'strictly_positive':hi<0?'strictly_negative':'includes_zero',
        alerts:summarizeAlerts(observations,n)};
      if (q.excluded===null) {
        const prior = primary.find(r=>r.benchmark===b&&r.cohort==='all12');
        compare(row,prior,['condition_count','observed_low_count','observed_any_count','observed_mean_H','fixed_reference_mean','fixed_reference_p','paired_D_mean','paired_D_95','paired_D_positive_fraction','paired_valid','paired_invalid']);
        const existingAlerts = JSON.parse(await fs.readFile(path.join(ROOT,'results/alerts/alerts_summary.json'),'utf8')).filter(r=>r.benchmark===b&&r.cohort==='Full12');
        for (const alert of row.alerts) compare(alert,existingAlerts.find(r=>r.rule===alert.rule),['trigger_dates','trigger_percent','episodes','first','last']);
      } else if (q.excluded==='211322000000') {
        const prior = expected.find(r=>r.benchmark===b&&r.L===L&&r.cohort==='without_Jianping11');
        compare(row,prior,['condition_count','observed_low_count','observed_any_count','observed_mean_H','fixed_reference_mean','fixed_reference_p','paired_D_mean','paired_D_95','paired_D_positive_fraction','paired_valid','paired_invalid']);
      }
      summary.push(row);
    }
    checks.push({benchmark:b,control_count_fields:countComparisons,all_twelve_primary_summary:'matched',without_Jianping_saved_summary:'matched',all_twelve_alerts:'matched'});
    console.log(JSON.stringify({benchmark:b,comparisons:prepared.length,draws:R,controls:'matched'}));
  }
  const deletions = summary.filter(r=>r.excluded_county_id!==null);
  if (deletions.length!==60 || new Set(deletions.map(r=>r.benchmark+'|'+r.excluded_county_id)).size!==60) throw Error('Symmetric coverage');
  const byBenchmark = Object.keys(BENCHMARKS).map(b=>{
    const rows = deletions.filter(r=>r.benchmark===b), positive = rows.filter(r=>r.interval_class==='strictly_positive');
    return {benchmark:b, benchmark_label:BENCHMARKS[b], comparisons:12,
      strictly_positive:positive.length, includes_zero:rows.filter(r=>r.interval_class==='includes_zero').length,
      strictly_negative:rows.filter(r=>r.interval_class==='strictly_negative').length,
      positive_exclusions:positive.map(r=>r.excluded_county),
      attainment_percent_range:[Math.min(...rows.map(r=>r.observed_attainment_percent)),Math.max(...rows.map(r=>r.observed_attainment_percent))],
      paired_mean_range:[Math.min(...rows.map(r=>r.paired_D_mean)),Math.max(...rows.map(r=>r.paired_D_mean))],
      aggregate_alert_date_range:[Math.min(...rows.map(r=>r.alerts[0].trigger_dates)),Math.max(...rows.map(r=>r.alerts[0].trigger_dates))]};
  });
  const report = {design:{analysis:'symmetric leave-one-county-out',benchmarks:5,counties:12,deletion_comparisons:60,all_twelve_controls:5,L,R,
    complete_monitoring_dates:204,scheduled_monitoring_dates:207,missing_dates:P.dates.slice(108).filter((_,i)=>!P.mask[108+i]),
    input_sha256:sha(input),saved_path_sha256:pathHashes,
    path_source:'Original saved L6 block paths and their accompanying historical coefficients',
    missing_rule:'Original complete twelve-county mask for every deletion; missing observations reset alerts',
    source_boundary_rule:'Source boundaries do not reset alerts while their conditions hold',
    aggregate_alert_rule:'Trigger from the third consecutive qualifying scheduled observation',
    interval_rule:'Strictly positive when the unrounded lower 95% endpoint exceeds zero; strictly negative when its upper endpoint is below zero; otherwise includes zero'},
    totals:{deletion_comparisons:deletions.length,
      strictly_positive:deletions.filter(r=>r.interval_class==='strictly_positive').length,
      includes_zero:deletions.filter(r=>r.interval_class==='includes_zero').length,
      strictly_negative:deletions.filter(r=>r.interval_class==='strictly_negative').length,
      no_valid_pairs:deletions.filter(r=>r.interval_class==='no_valid_pairs').length},
    by_benchmark:byBenchmark,controls:checks,comparisons:summary};
  if (Object.entries(report.totals).filter(([k])=>k!=='deletion_comparisons').reduce((a,[,v])=>a+v,0)!==60) throw Error('Interval classification conservation');
  await fs.mkdir(outputDir,{recursive:true});
  await fs.writeFile(path.join(outputDir,'county_influence_summary.json'),JSON.stringify(report,null,2)+'\n');
  const header = ['benchmark','benchmark_label','excluded_county_id','excluded_county','counties','condition_count','observed_attainment_percent','observed_mean_H','fixed_reference_mean','fixed_reference_p','fixed_tail_count','paired_D_mean','paired_D_95_low','paired_D_95_high','paired_D_positive_fraction','positive_count','zero_count','negative_count','paired_valid','paired_invalid','interval_class','aggregate_alert_dates','aggregate_alert_episodes','third_alert_dates','third_alert_episodes','half_alert_dates','half_alert_episodes'];
  const quote = value => {const v = value===null?'':String(value);return /[,"\r\n]/.test(v)?'"'+v.replaceAll('"','""')+'"':v;};
  const csv = header.join(',')+'\n'+summary.map(r=>{
    const flat = {...r,paired_D_95_low:r.paired_D_95[0],paired_D_95_high:r.paired_D_95[1],aggregate_alert_dates:r.alerts[0].trigger_dates,aggregate_alert_episodes:r.alerts[0].episodes,third_alert_dates:r.alerts[1].trigger_dates,third_alert_episodes:r.alerts[1].episodes,half_alert_dates:r.alerts[2].trigger_dates,half_alert_episodes:r.alerts[2].episodes};
    return header.map(k=>quote(flat[k])).join(',');
  }).join('\n')+'\n';
  await fs.writeFile(path.join(outputDir,'county_influence_summary.csv'),csv);
  console.log(JSON.stringify({status:'PASS',comparisons:summary.length,totals:report.totals,by_benchmark:byBenchmark,output_dir:outputDir}));
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  await run(path.resolve(ROOT,process.env.COUNTY_INFLUENCE_OUT || 'results/supplementary_validation'));
}
