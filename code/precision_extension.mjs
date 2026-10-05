import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const INPUT=path.join(ROOT,'inputs');
const OUT=path.resolve(ROOT,process.env.PRECISION_OUT||'results/precision');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>fs.readFile(path.join(INPUT,'reference_experiments',p),'utf8');
const inert=async p=>{const h=await read(p),m=h.match(/<script\b[^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/);if(!m)throw Error('JSON missing '+p);return JSON.parse(m[1]);};
const core=await fs.readFile(path.join(ROOT,'code/reference_core.js'),'utf8');
const text=await read('T1_source/text_csv.js');
const guard=await read('T1_source/record_schema.js');
const science=new Function(core+text+guard+'\nreturn {PCG32,panelFromCsv,parseCsv,estimateB,baselineIndices,cohortColumns,postStats,residuals,referenceStats,drawStarts,groupRecord,decodeReplicatePart,quantile,mean};')();
const csv=await fs.readFile(path.join(INPUT,'normalized_prices.csv'));
if(sha(csv)!=='f5536401160dc415b33ee7934081484a208aaefc1fa7fd7c6eff6a8b822a906b')throw Error('input SHA');
const P=science.panelFromCsv(csv.toString('utf8'),science.parseCsv);
const selection={B0:['all12','without_Jianping11','screened6'],B2:['without_Jianping_Qingyuan10','screened6'],B4:['without_Jianping11']};
const FIELDS=['condition_count','observed_count','reference_count','observed_any_count','reference_any_count','fixed_reference_count','fixed_reference_any_count'];
const summaries=[],checks=[];
await fs.mkdir(OUT,{recursive:true});
async function write(name,value){await fs.writeFile(path.join(OUT,name),typeof value==='string'||Buffer.isBuffer(value)?value:JSON.stringify(value,null,2)+'\n');}
function validate(r,N,F){const T=r.condition_count;if(!Number.isInteger(T)||T<0||T>207)throw Error('T');for(const k of FIELDS){const v=r[k];if(v!==null&&(!Number.isInteger(v)||v<0||v>=65535))throw Error('count domain');}
 for(const [k,a,t]of [['observed_count','observed_any_count',T],['reference_count','reference_any_count',T],['fixed_reference_count','fixed_reference_any_count',F]]){if((r[k]===null)!==(r[a]===null))throw Error('partial null');if(r[k]!==null&&(r[k]>N*t||r[a]>t||r[a]>r[k]||r[k]>N*r[a]))throw Error('count bound');}
 if(T===0&&(r.observed_count!==0||r.observed_any_count!==0||r.reference_count!==null||r.reference_any_count!==null))throw Error('empty T');if(F===0&&(r.fixed_reference_count!==null||r.fixed_reference_any_count!==null))throw Error('empty F');if(T>0&&(r.observed_count===null||r.reference_count===null))throw Error('valid T');if(F>0&&r.fixed_reference_count===null)throw Error('valid F');}
function derived(r,N,F){const T=r.condition_count;return {...r,observed:T?r.observed_count/(N*T):null,reference:T?r.reference_count/(N*T):null,D:T?(r.observed_count-r.reference_count)/(N*T):null,fixed_reference:F?r.fixed_reference_count/(N*F):null};}
const catalogue=JSON.parse(await read('T1_source/actual_records_catalogue.json'));
for(const [b,names]of Object.entries(selection)){
 const packet=await inert('T1_indices/T1_'+b+'_L6_indices_rep1_1999.html'),m=packet.metadata,old=Buffer.from(packet.base64,'base64');
 if(sha(old)!==m.whole_group_sha256||old.length!==1999*m.record_width)throw Error('old index hash/shape');
 const bytes=new Uint8Array(9999*m.record_width);bytes.set(old);const rng=m.group_state_after.map(science.PCG32.restore);
 for(let rep=1999;rep<9999;rep++){const draws=['outer','inner','fixed'].map((layer,i)=>science.drawStarts(P,b,6,layer,rng[i]));let at=rep*m.record_width;for(const d of draws){bytes.set(d.starts,at);at+=d.starts.length;}}
 if(sha(Buffer.from(bytes.slice(0,old.length)))!==m.whole_group_sha256)throw Error('prefix changed');
 const I={...m,benchmark:b,L:6,R:9999,bytes};
 const im={...m,schema:'precision_indices_v1',group_repetitions:9999,rep_end:9999,records:9999,whole_group_sha256:sha(Buffer.from(bytes)),prefix_1999_sha256:sha(old),extension_start:2000,resumed_states:m.group_state_after,new_group_state_after:rng.map(r=>r.snapshot()),actual_paths:9999*3,record_encoding:'Uint8 starts; outer/inner/fixed per repetition; expand noncircular L6, trim final block only'};
 await write(b+'_L6_indices.u8',Buffer.from(bytes));await write(b+'_L6_indices_metadata.json',im);
 const saved=[];for(const p of catalogue.files.filter(p=>p.metadata.benchmark===b&&p.metadata.L===6).sort((a,b)=>a.metadata.rep_start-b.metadata.rep_start)){const packet=await inert('T1_records/'+p.title+'.html');saved.push(...science.decodeReplicatePart(packet,v=>new Uint8Array(Buffer.from(v,'base64'))));}
 if(saved.length!==1999*3)throw Error('old rows');const oldBy=new Map(saved.map(r=>[r.rep+'|'+r.cohort,r]));
 const t4=await inert('T4b_records/T4b_'+b+'_rep1_1999.html'),t4bytes=Buffer.from(t4.counts_u16_le_base64,'base64');if(sha(t4bytes)!==t4.counts_sha256)throw Error('T4 count hash');
 const oldS6=new Map();for(let rep=1;rep<=1999;rep++){const r={rep};for(let j=0;j<7;j++){const v=t4bytes.readUInt16LE(((rep-1)*3+2)*14+j*2);r[FIELDS[j]]=v===65535?null:v;}oldS6.set(rep,r);}
 const fixedB=science.estimateB(P,b,science.baselineIndices(b));const prepared=names.map(name=>{const cols=science.cohortColumns(name),obs=science.postStats(P,b,fixedB,cols);return {name,cols,obs,res:science.residuals(P,b,fixedB,cols),rows:[]};});
 const width=b==='B4'?144:12,coefBuffer=Buffer.alloc(9999*width*8);let prefixCountComparisons=0,coefDiff=0,coefMax=0;
 for(let rep=0;rep<9999;rep++){
  const paths=science.groupRecord(I,rep),computedB=science.estimateB(P,b,paths.outer),savedB=rep<1999?oldBy.get((rep+1)+'|all12').bStar:null,bStar=savedB||computedB;
  const flat=bStar.flat();for(let j=0;j<width;j++)coefBuffer.writeDoubleLE(flat[j],(rep*width+j)*8);
  if(savedB){const a=computedB.flat(),z=savedB.flat();for(let j=0;j<width;j++){const d=Math.abs(a[j]-z[j]);if(d>1e-12)throw Error('coefficient tolerance');if(!Object.is(a[j],z[j]))coefDiff++;coefMax=Math.max(coefMax,d);}}
  for(const q of prepared){const obs=science.postStats(P,b,bStar,q.cols),ref=science.referenceStats(obs,science.residuals(P,b,bStar,q.cols),paths.inner),fref=science.referenceStats(q.obs,q.res,paths.fixed);
   const actual={rep:rep+1,condition_count:obs.condition_count,observed_count:obs.low_count,reference_count:ref.low_count,observed_any_count:obs.any_count,reference_any_count:ref.any_count,fixed_reference_count:fref.low_count,fixed_reference_any_count:fref.any_count};validate(actual,q.cols.length,q.obs.condition_count);
   let r=actual;if(rep<1999){const prior=q.name==='screened6'?oldS6.get(rep+1):oldBy.get((rep+1)+'|'+q.name);for(const k of FIELDS){if(actual[k]!==prior[k])throw Error('prefix scientific count '+b+'/'+q.name+'/'+(rep+1)+'/'+k);prefixCountComparisons++;}r=Object.fromEntries(['rep',...FIELDS].map(k=>[k,prior[k]]));}q.rows.push(derived(r,q.cols.length,q.obs.condition_count));
  }
  if((rep+1)%1000===0)console.log(JSON.stringify({benchmark:b,scored:rep+1,cohorts:names.length}));
 }
 await write(b+'_L6_bStar.f64le',coefBuffer);
 for(const q of prepared){const f=q.rows.filter(r=>r.fixed_reference_count!==null),d=q.rows.filter(r=>r.D!==null),fvals=f.map(r=>r.fixed_reference),ds=d.map(r=>r.D),K=f.filter(r=>r.fixed_reference_count>=q.obs.low_count).length,pos=d.filter(r=>r.observed_count>r.reference_count).length,zero=d.filter(r=>r.observed_count===r.reference_count).length;
  const s={benchmark:b,cohort:q.name,counties:q.cols.length,L:6,requested:9999,fixed_T:q.obs.condition_count,fixed_O:q.obs.low_count,observed_mean_H:q.obs.observed_mean_H,fixed_reference_mean:science.mean(fvals),fixed_reference_90:[science.quantile(fvals,.05),science.quantile(fvals,.95)],fixed_reference_95:[science.quantile(fvals,.025),science.quantile(fvals,.975)],fixed_tail_count:K,fixed_valid:f.length,fixed_p:f.length?(K+1)/(f.length+1):null,paired_valid:d.length,paired_invalid:9999-d.length,paired_D_mean:science.mean(ds),paired_D_95:[science.quantile(ds,.025),science.quantile(ds,.975)],positive_count:pos,zero_count:zero,negative_count:d.length-pos-zero,positive_fraction:d.length?pos/d.length:null,precision_only:true,primary_draws:1999};
  summaries.push(s);const header=['rep','N','fixed_T',...FIELDS,'observed','reference','D','fixed_reference'];await write(b+'_'+q.name+'_9999.csv',header.join(',')+'\n'+q.rows.map(r=>header.map(k=>k==='N'?q.cols.length:k==='fixed_T'?q.obs.condition_count:r[k]??'').join(',')).join('\n')+'\n');
 }
 checks.push({benchmark:b,prefix_indices_sha256:sha(old),prefix_equal:true,prefix_count_comparisons:prefixCountComparisons,prefix_count_errors:0,old_coefficients_retained:true,cross_engine_coefficient_differences:coefDiff,cross_engine_max_abs_difference:coefMax,indices_sha256:sha(Buffer.from(bytes)),coefficient_sha256:sha(coefBuffer),new_state_after:im.new_group_state_after});
 await write('precision_summary.json',summaries);await write('prefix_and_engine_checks.json',checks);
}
await write('execution.json',{status:'PASS',input_path:path.join(INPUT,'normalized_prices.csv'),input_sha256:sha(csv),output_path:OUT,cwd:process.cwd(),node:process.version,core_sha256:sha(core),configurations:summaries.length,rows:6*9999,requested_total:9999,checks});console.log(JSON.stringify({status:'PASS',configurations:summaries.length,rows:6*9999,OUT}));
