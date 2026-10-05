import fs from 'node:fs/promises';import path from 'node:path';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),INPUT=path.join(ROOT,'inputs/normalized_prices.csv'),OUT=path.resolve(ROOT,process.env.ALERT_OUT||'results/alerts');
const core=await fs.readFile(path.join(ROOT,'code/reference_core.js'),'utf8'),text=await fs.readFile(path.join(ROOT,'inputs/reference_experiments/T1_source/text_csv.js'),'utf8');
const s=new Function(core+text+'\nreturn {panelFromCsv,parseCsv,cohortColumns,estimateB,baselineIndices,rowB,MAIN12};')();
const raw=await fs.readFile(INPUT),sha=crypto.createHash('sha256').update(raw).digest('hex');if(sha!=='f5536401160dc415b33ee7934081484a208aaefc1fa7fd7c6eff6a8b822a906b')throw Error('input SHA');
const P=s.panelFromCsv(raw.toString('utf8'),s.parseCsv),rows=[],summary=[];
const cohorts={Full12:'all12',U10:'without_Jianping_Qingyuan10',S6:'screened6'};
const prices=new Map(P.raw.map(r=>[[r.date,r.region,r.product].join('|'),r]));
function endpoint(v){const dates=v.filter(r=>r.trigger).map(r=>r.date);return {trigger_dates:dates.length,trigger_percent:dates.length/204*100,episodes:v.filter(r=>r.episode_start).length,first:dates[0]??null,last:dates.at(-1)??null};}
for(const b of ['B0','B1','B2','B3','B4'])for(const [label,name]of Object.entries(cohorts)){
 const cols=s.cohortColumns(name),N=cols.length,coef=s.estimateB(P,b,s.baselineIndices(b));let belowRun=0,previous=[false,false,false],series=[[],[],[]];
 for(let pt=0;pt<207;pt++){const t=108+pt,date=P.dates[t],valid=P.mask[t],base=s.rowB(P,b,coef,t),g=valid?cols.map(j=>P.x[t][j]-base[j]):null,G=valid?g.reduce((a,b)=>a+b,0)/N:null,k=valid?g.filter(v=>v<-1e-12).length:null;
  belowRun=valid&&G<-1e-12?belowRun+1:0;
  const triggers=[valid&&belowRun>=3,valid&&3*k>=N,valid&&2*k>=N];if(triggers[2]&&!triggers[1])throw Error('subset');
  const signature=cols.map(j=>{const c=prices.get([date,s.MAIN12[j],'maize_purchase_mixed'].join('|')),u=prices.get([date,s.MAIN12[j],'urea_domestic'].join('|'));return (c?.source??'')+'/'+(u?.source??'');}).join(';');
  const priorSig=pt?rows.at(-1)?.source_signature:null;
  const r={benchmark:b,cohort:label,date,N,valid,G,k,required_third:Math.ceil(N/3),required_half:Math.ceil(N/2),below_run:belowRun,source_signature:signature,source_boundary:pt>0&&signature!==priorSig,rule_i:triggers[0],rule_third:triggers[1],rule_half:triggers[2],rule_i_start:triggers[0]&&!previous[0],rule_third_start:triggers[1]&&!previous[1],rule_half_start:triggers[2]&&!previous[2]};rows.push(r);
  for(let q=0;q<3;q++)series[q].push({date,trigger:triggers[q],episode_start:triggers[q]&&!previous[q]});previous=triggers;
 }
 for(let q=0;q<3;q++)summary.push({benchmark:b,cohort:label,N,rule:['aggregate_three_dates','H_ge_third','H_ge_half'][q],complete_monitoring_dates:204,...endpoint(series[q])});
}
if(rows.length!==3105||rows.filter(r=>r.valid).length!==3060)throw Error('calendar counts');
await fs.mkdir(OUT,{recursive:true});const keys=Object.keys(rows[0]);const csv=keys.join(',')+'\n'+rows.map(r=>keys.map(k=>r[k]===null?'':typeof r[k]==='boolean'?Number(r[k]):r[k]).join(',')).join('\n')+'\n';await fs.writeFile(path.join(OUT,'alerts_daily.csv'),csv);await fs.writeFile(path.join(OUT,'alerts_summary.json'),JSON.stringify(summary,null,2)+'\n');
await fs.writeFile(path.join(OUT,'execution.json'),JSON.stringify({status:'PASS',INPUT,OUT,cwd:process.cwd(),input_sha256:sha,node:process.version,planned_rows:3105,valid_rows:3060,missing_dates:P.dates.slice(108).filter((d,i)=>!P.mask[108+i]),half_subset:true,episode_count_monotonicity:'not assumed'},null,2)+'\n');console.log(JSON.stringify({status:'PASS',rows:3105,valid:3060,summary}));
