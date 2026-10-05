// PCG32 component: Copyright (c) 2014 M. E. O'Neill; Apache License 2.0.
// Adapted to JavaScript BigInt with state serialization. See THIRD_PARTY_NOTICES.md.
// The statistical routines outside the PCG32 component are project contributions.

const MASK64=(1n<<64n)-1n, MASK32=(1n<<32n)-1n;
class PCG32 {
 constructor(initstate,initseq){const s=BigInt(initstate),q=BigInt(initseq);if(s<0n||s>MASK64||q<0n||q>=(1n<<63n))throw new RangeError("invalid seed");this.state=0n;this.inc=(q<<1n)|1n;this.nextU32();this.state=(this.state+s)&MASK64;this.nextU32();}
 nextU32(){const old=this.state;this.state=(old*6364136223846793005n+this.inc)&MASK64;const x=Number((((old>>18n)^old)>>27n)&MASK32),rot=Number(old>>59n);return ((x>>>rot)|(x<<((-rot)&31)))>>>0;}
 randbelow(bound){if(!Number.isInteger(bound)||bound<1||bound>0xffffffff)throw new RangeError("invalid bound");const threshold=0x100000000%bound;for(;;){const r=this.nextU32();if(r>=threshold)return r%bound;}}
 snapshot(){return {state:this.state.toString(),inc:this.inc.toString()};}
 static restore(s){const r=Object.create(PCG32.prototype);r.state=BigInt(s.state);r.inc=BigInt(s.inc);if(r.state<0n||r.state>MASK64||r.inc<1n||r.inc>MASK64||(r.inc&1n)!==1n)throw new RangeError("invalid snapshot");return r;}
}
const TOL=1e-12,R=9999,SEED=20261002;
const MAIN12=["210111000000","210124000000","210283000000","210423000000","210682000000","210882000000","210922000000","211081000000","211121000000","211224000000","211282000000","211322000000"];
const COHORTS={all12:MAIN12,without_Jianping11:MAIN12.filter(x=>x!=="211322000000"),without_Jianping_Qingyuan10:MAIN12.filter(x=>!["211322000000","210423000000"].includes(x))};
const BOUNDS={B0:[0,108],B1:[36,108],B2:[72,108],B3:[0,72],B4:[0,108]};
function mean(v){return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;}
function quantile(v,p){const z=v.filter(Number.isFinite).slice().sort((a,b)=>a-b);if(!z.length)return null;const h=(z.length-1)*p,i=Math.floor(h),f=h-i;return z[i]+f*(z[Math.min(i+1,z.length-1)]-z[i]);}
function panelFromCsv(csv,parseCsv){
 const rows=parseCsv(csv),header=rows.shift().map((x,i)=>i?x:x.replace(/^\uFEFF/,"")),idx=Object.fromEntries(header.map((x,i)=>[x,i]));
 if(rows.length!==9450)throw Error("canonical row count");
 const dates=[...new Set(rows.map(r=>r[idx.date]))].sort(),m=new Map(),raw=[];
 for(const r of rows){const item={date:r[idx.date],region:r[idx.region_id],product:r[idx.product_id],value:r[idx.value],original_value:r[idx.original_value],source:r[idx.source_id],status:r[idx.status]};const key=[item.date,item.region,item.product].join("|");if(m.has(key))throw Error("duplicate canonical quote");m.set(key,item);raw.push(item);}
 if(dates.length!==315||dates[0]!=="2018-01-05"||dates.at(-1)!=="2026-09-25")throw Error("canonical calendar");
 const x=dates.map(date=>MAIN12.map(region=>{const c=m.get([date,region,"maize_purchase_mixed"].join("|")),u=m.get([date,region,"urea_domestic"].join("|"));return c&&u&&c.value!==""&&u.value!==""&&+c.value>0&&+u.value>0&&c.source===u.source?Math.log(+c.value)-Math.log(+u.value):null;}));
 const mask=x.map(row=>row.every(Number.isFinite));
 if(mask.slice(0,108).filter(Boolean).length!==108||mask.slice(108).filter(Boolean).length!==204)throw Error("main12 masks");
 const slot=dates.map(date=>({month:+date.slice(5,7),day:+date.slice(8,10),year:+date.slice(0,4)}));
 return {dates,x,mask,slot,raw};
}
function cohortColumns(name){const ids=COHORTS[name];if(!ids)throw Error("cohort");return ids.map(id=>MAIN12.indexOf(id));}
function baselineIndices(b){const [start,end]=BOUNDS[b];return Array.from({length:end-start},(_,i)=>start+i);}
function estimateB(P,b,indices){
 if(b==="B4"){const out=Array.from({length:12},()=>Array(12).fill(0)),counts=Array(12).fill(0);for(let target=0;target<indices.length;target++){const month=P.slot[target].month-1;counts[month]++;for(let j=0;j<12;j++)out[month][j]+=P.x[indices[target]][j];}for(let m=0;m<12;m++){if(!counts[m])throw Error("empty B4 target month");for(let j=0;j<12;j++)out[m][j]/=counts[m];}return out;}
 const out=Array(12).fill(0);for(const i of indices)for(let j=0;j<12;j++)out[j]+=P.x[i][j];return out.map(v=>v/indices.length);
}
function rowB(P,b,coef,t){return b==="B4"?coef[P.slot[t].month-1]:coef;}
function postStats(P,b,coef,cols){
 let count=0,low_count=0,any_count=0;const G=Array(207).fill(null),condition=Array(207).fill(false);
 for(let pt=0;pt<207;pt++){const t=108+pt;if(!P.mask[t])continue;const base=rowB(P,b,coef,t),g=cols.map(c=>P.x[t][c]-base[c]),meanG=mean(g);G[pt]=meanG;if(meanG>=-TOL){condition[pt]=true;count++;const k=g.filter(z=>z<-TOL).length;low_count+=k;any_count+=k>0?1:0;}}
 return {condition_count:count,counties:cols.length,low_count,any_count,observed_mean_H:count?low_count/(count*cols.length):null,observed_any:count?any_count/count:null,G,condition};
}
function residuals(P,b,coef,cols){
 return P.x.slice(0,108).map((row,t)=>{const base=rowB(P,b,coef,t),g=cols.map(c=>row[c]-base[c]),G=mean(g);return g.map(v=>v-G);});
}
function referenceStats(observed,residual,indices){
 if(!observed.condition_count)return {reference_mean_H:null,reference_any:null,low_count:null,any_count:null};
 let low_count=0,any_count=0;for(let pt=0;pt<207;pt++){if(!observed.condition[pt])continue;const row=residual[indices[pt]];if(row.length!==observed.counties)throw Error("reference county count");const k=row.filter(v=>observed.G[pt]+v<-TOL).length;low_count+=k;any_count+=k>0?1:0;}
 return {reference_mean_H:low_count/(observed.condition_count*observed.counties),reference_any:any_count/observed.condition_count,low_count,any_count};
}
function donorCandidates(P,b,L,targetStart,layer){
 const base=baselineIndices(b);if(b!=="B4")return base.slice(0,base.length-L+1);
 const target=layer==="outer"?targetStart:108+targetStart,slot=P.slot[target];
 return base.filter(i=>i+L<=108&&P.slot[i].month===slot.month&&P.slot[i].day===slot.day&&(layer!=="outer"||P.slot[i].year===P.slot[i+L-1].year));
}
function drawStarts(P,b,L,layer,rng){
 const n=layer==="outer"?baselineIndices(b).length:207,starts=[],support=[];
 for(let pos=0;pos<n;pos+=L){const candidates=donorCandidates(P,b,L,pos,layer);support.push(candidates.length);if(!candidates.length)throw Error("zero donors "+[b,L,layer,pos]);starts.push(candidates[rng.randbelow(candidates.length)]);}
 return {starts,support};
}
function expandStarts(starts,L,n){const out=[];for(const s of starts)for(let j=0;j<L&&out.length<n;j++)out.push(s+j);if(out.length!==n)throw Error("path length");return out;}
function streamConfig(b,L,layer){
 const bi=Number(b.slice(1)),li=[3,6,12].indexOf(L),la={fixed:0,outer:1,inner:2}[layer],add={fixed:43000,outer:41000,inner:42000}[layer];if(li<0||la===undefined)throw Error("stream config");
 return {rng_version:"pcg32-xsh-rr64-32-v1",benchmark:b,L,layer,initstate:String(SEED+add+100*bi+L),initseq:String(1+100*bi+10*li+la)};
}
function generateGroupIndices(P,b,L){
 const n=baselineIndices(b).length,nb=Math.ceil(n/L),ni=Math.ceil(207/L),record_width=nb+2*ni;
 const configs=["outer","inner","fixed"].map(layer=>streamConfig(b,L,layer)),rngs=configs.map(c=>new PCG32(c.initstate,c.initseq)),before=rngs.map(r=>r.snapshot()),bytes=new Uint8Array(R*record_width);let support={};
 for(let rep=0;rep<R;rep++){const outer=drawStarts(P,b,L,"outer",rngs[0]),inner=drawStarts(P,b,L,"inner",rngs[1]),fixed=drawStarts(P,b,L,"fixed",rngs[2]),offset=rep*record_width;bytes.set(outer.starts,offset);bytes.set(inner.starts,offset+nb);bytes.set(fixed.starts,offset+nb+ni);if(!rep)support={outer:outer.support,inner:inner.support,fixed:fixed.support};}
 return {benchmark:b,L,R,configs,before,after:rngs.map(r=>r.snapshot()),outer_n:n,nb,ni,record_width,bytes,support,encoding:"Uint8 actual global donor block starts in per-replicate outer/inner/fixed order; expand every start s to s..s+L-1, trim only final block to target n. This lossless representation contains all actual path indices."};
}
function groupRecord(I,rep){if(rep<0||rep>=I.R)throw Error("rep");const offset=rep*I.record_width,outer=Array.from(I.bytes.slice(offset,offset+I.nb)),inner=Array.from(I.bytes.slice(offset+I.nb,offset+I.nb+I.ni)),fixed=Array.from(I.bytes.slice(offset+I.nb+I.ni,offset+I.record_width));return {outer:expandStarts(outer,I.L,I.outer_n),inner:expandStarts(inner,I.L,207),fixed:expandStarts(fixed,I.L,207)};}
function evaluateReplicate(P,I,rep,name){
 const b=I.benchmark,cols=cohortColumns(name),paths=groupRecord(I,rep),fixedB=estimateB(P,b,baselineIndices(b)),obs0=postStats(P,b,fixedB,cols),fixedRef=referenceStats(obs0,residuals(P,b,fixedB,cols),paths.fixed),bStar=estimateB(P,b,paths.outer),obs=postStats(P,b,bStar,cols),ref=referenceStats(obs,residuals(P,b,bStar,cols),paths.inner);
 return {rep:rep+1,cohort:name,counties:cols.length,condition_count:obs.condition_count,observed_count:obs.low_count,reference_count:ref.low_count,observed_any_count:obs.any_count,reference_any_count:ref.any_count,observed:obs.observed_mean_H,reference:ref.reference_mean_H,D:obs.condition_count?(obs.low_count-ref.low_count)/(cols.length*obs.condition_count):null,observed_any:obs.observed_any,reference_any:ref.reference_any,fixed_reference:fixedRef.reference_mean_H,fixed_reference_any:fixedRef.reference_any,fixed_reference_count:fixedRef.low_count,fixed_reference_any_count:fixedRef.any_count,bStar};
}
function summarizeGroup(P,I,rows,name){
 const b=I.benchmark,cols=cohortColumns(name),coef=estimateB(P,b,baselineIndices(b)),obs=postStats(P,b,coef,cols),z=rows.filter(r=>r.cohort===name);
 if(z.length!==R||new Set(z.map(r=>r.rep)).size!==R||z.some(r=>r.rep<1||r.rep>R))throw Error("replicate completeness");
 const paired=z.filter(r=>Number.isFinite(r.D)),D=paired.map(r=>r.D),fixed=z.filter(r=>Number.isInteger(r.fixed_reference_count)),f=fixed.map(r=>r.fixed_reference),any=z.filter(r=>Number.isInteger(r.fixed_reference_any_count)),a=any.map(r=>r.fixed_reference_any);
 return {benchmark:b,cohort:name,counties:cols.length,L:I.L,R,condition_count:obs.condition_count,observed_low_count:obs.low_count,observed_any_count:obs.any_count,observed_mean_H:obs.observed_mean_H,observed_any:obs.observed_any,fixed_reference_mean:mean(f),fixed_reference_90:[quantile(f,.05),quantile(f,.95)],fixed_reference_95:[quantile(f,.025),quantile(f,.975)],fixed_reference_p:fixed.length?(1+fixed.filter(r=>r.fixed_reference_count>=obs.low_count).length)/(1+fixed.length):null,fixed_reference_valid:fixed.length,fixed_reference_any_mean:mean(a),fixed_reference_any_90:[quantile(a,.05),quantile(a,.95)],fixed_reference_any_p:any.length?(1+any.filter(r=>r.fixed_reference_any_count>=obs.any_count).length)/(1+any.length):null,paired_D_mean:mean(D),paired_D_95:[quantile(D,.025),quantile(D,.975)],paired_D_positive_fraction:paired.length?paired.filter(r=>r.observed_count>r.reference_count).length/paired.length:null,paired_valid:paired.length,paired_invalid:R-paired.length,counting_implementation:"count-rational-v1"};
}

COHORTS.screened6=["210124000000","210283000000","210682000000","211081000000","211224000000","211282000000"];
