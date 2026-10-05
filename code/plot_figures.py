#!/usr/bin/env python3
"""Replot archived inputs only. No resampling or scientific refit."""
from pathlib import Path
import importlib.util,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from datetime import datetime
from scipy.stats import beta

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'inputs/reference_experiments/figure_export/inputs'
HP=ROOT/'code/frozen_figure_helpers.py'
spec=importlib.util.spec_from_file_location('frozen_helper',HP);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
ix=json.loads((IN/'source_index.json').read_text(encoding='utf-8'))['inputs']
summary=h.carrier(IN,ix['t1_summary'])['summary'];primary=h.validate_t1(summary)
t4=h.carrier(IN,ix['t4b_summary'])['summary'];h.validate_t4b(t4)
panels=[h.carrier(IN,ix['panel'+str(i)])['data'] for i in (1,2,3)];h.validate_panels(panels)
arrays=h.hist_arrays([h.carrier(IN,ix[k]) for k in ('t1_b0_rep1_1000','t1_b0_rep1001_1999')],primary)
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'ps.fonttype':42})
colors=['#0072B2','#D55E00','#009E73'];labels=['Full12','U10','S6'];bench=['B0','B1','B2','B3','B4'];records=[]
def save(fig,name):
 records.extend(h.save_figure(fig,name,OUT,600))
def tail_ci(p,R=1999):
 k=int(round(p*(R+1)-1))
 if k==0:return 0,1-.05**(1/R)
 if k==R:return .05**(1/R),1
 return beta.ppf(.025,k,R-k+1),beta.ppf(.975,k+1,R-k)

# Main Figure 1: categorical benchmarks, point estimates and error bars only.
fig,axes=plt.subplots(2,2,figsize=(10,7.5));xs=np.arange(5)
for j,c in enumerate(['all12','without_Jianping_Qingyuan10','screened6']):
 rr=[primary[(b,c)] if c!='screened6' else next(r for r in t4 if r['benchmark']==b and r['counties']==6) for b in bench]
 for i,r in enumerate(rr):
  x=i+(j-1)*.19;col=colors[j]
  axes[0,0].plot(x,r['condition_count']/204*100,'o',color=col,ms=5,label=labels[j] if i==0 else None)
  axes[0,1].plot(x,r['observed_mean_H']*100,'o',color=col,ms=5)
  lo,hi=np.array(r['fixed_reference_90'])*100;y=r['fixed_reference_mean']*100
  axes[0,1].errorbar(x,y,yerr=[[y-lo],[hi-y]],fmt='s',mfc='white',color=col,ms=4,capsize=2)
  p=r['fixed_reference_p'];l,u=tail_ci(p)
  axes[1,0].vlines(x,max(l,.00005),u,color=col,lw=1.4)
  axes[1,0].plot(x,p,'v' if p==.0005 else '^' if p==1 else 'o',color=col,ms=5)
  lo,hi=np.array(r['paired_D_95'])*100;y=r['paired_D_mean']*100
  axes[1,1].errorbar(x,y,yerr=[[y-lo],[hi-y]],fmt='o',color=col,ms=5,capsize=3)
axes[0,0].set_ylabel('Aggregate attainment (% of 204 dates)')
axes[0,1].set_ylabel('Conditional mean H (%)')
axes[0,1].set_title('Circles: observed; open squares: reference',fontsize=9)
axes[1,0].set_ylabel('Fixed-reference upper-tail probability')
axes[1,0].set_yscale('log');axes[1,0].set_ylim(.000045,1.45);axes[1,0].axhline(.05,color='#888',ls=':',lw=.8)
axes[1,0].set_title('Triangles denote boundary counts; bars: binomial 95%',fontsize=8.5)
axes[1,1].set_ylabel('Paired difference D (percentage points)');axes[1,1].axhline(0,color='#777',ls='--',lw=1)
for ax,letter in zip(axes.flat,'abcd'):
 ax.set_xticks(xs,bench);h.style_axis(ax);ax.text(-.12,1.03,letter,transform=ax.transAxes,fontweight='bold')
fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
fig.tight_layout(rect=(0,.065,1,1));save(fig,'Figure_1')

# Main Figure 2: independently masked urea series; no cross-gap connections.
fig,axes=plt.subplots(3,1,figsize=(9.3,8.4),sharex=True)
for j in (0,1):
 rows=panels[j]['rows'];name=['Jianping','Qingyuan'][j]
 h.panel_line(axes[j],rows,'own_log_normalized',lambda i,r:r['own_line_connect_previous'],colors[j],name)
 h.panel_line(axes[j],rows,'other11_log_normalized',lambda i,r,rows=rows:not r['source_break'] and r['other11_valid']==11 and rows[i-1]['other11_valid']==11,'#777','Other eleven counties median',ls='--')
 axes[j].set_title(chr(97+j)+'  '+name+' urea',loc='left',y=1.32 if j==0 else 1.02)
rows=panels[0]['rows'];h.panel_line(axes[2],rows,'national_log_normalized',lambda i,r:r['national_line_connect_previous'],'#CC79A7','National urea')
axes[2].set_title('c  National urea circulation-market survey',loc='left')
for ax in axes:
 h.style_axis(ax);ax.set_ylabel('Log price relative to\nown January 2018 mean');ax.axvline(datetime(2024,2,5),color='#999',lw=.9,ls=':')
for a,b,l,y in [('2022-04-15','2024-11-15','94 equal observations',1.04),('2024-12-05','2026-02-15','44 equal observations',1.17)]:
 a,b=datetime.fromisoformat(a),datetime.fromisoformat(b);axes[0].plot([a,b],[y,y],transform=axes[0].get_xaxis_transform(),color='#333',clip_on=False,lw=1.2)
 axes[0].text(a+(b-a)/2,y+.02,l,transform=axes[0].get_xaxis_transform(),ha='center',fontsize=8,clip_on=False)
gap=datetime(2024,11,25);axes[0].axvline(gap,color=colors[1],ls='--',lw=.8)
axes[0].text(gap,.02,'25 Nov 2024 missing',rotation=90,transform=axes[0].get_xaxis_transform(),ha='right',va='bottom',fontsize=7.5)
axes[2].xaxis.set_major_locator(mdates.YearLocator());axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
handles=[Line2D([],[],color=colors[0],label='Jianping'),Line2D([],[],color=colors[1],label='Qingyuan'),Line2D([],[],color='#777',ls='--',label='Other eleven median (focal county excluded)'),Line2D([],[],color='#CC79A7',label='National urea')]
fig.legend(handles=handles,loc='lower center',ncol=2,frameon=False,fontsize=9)
fig.subplots_adjust(left=.14,right=.985,top=.86,bottom=.10,hspace=.55);save(fig,'Figure_2')

# Supplemental Figure S1: original 1,999 draws, no precision-check substitution.
fig,axes=plt.subplots(2,3,figsize=(10.2,6.4),sharey='row')
for j,c in enumerate(h.COHORTS):
 r=primary[('B0',c)];a,d=arrays[c]
 for row,values,key in [(0,a,'fixed_reference_90'),(1,d,'paired_D_95')]:
  ax=axes[row,j];ax.hist(values*100,bins=26,color=colors[j],alpha=.7,edgecolor='white',lw=.4)
  lo,hi=np.array(r[key])*100;ax.axvspan(lo,hi,color='#777',alpha=.12)
  ax.axvline(r['observed_mean_H']*100 if row==0 else 0,color='#333',ls='-' if row==0 else '--',lw=1.5);h.style_axis(ax)
  ax.set_xlabel('Reference mean H (%)' if row==0 else 'Paired D (percentage points)')
 axes[0,j].set_title(['Full12','N11','U10'][j])
axes[0,0].set_ylabel('Draws');axes[1,0].set_ylabel('Draws');fig.tight_layout();save(fig,'Figure_S1')

# Supplemental Figure S2: exact maize panel and connection masks.
fig,ax=plt.subplots(figsize=(9.3,4.7));rows=panels[2]['rows']
h.panel_line(ax,rows,'own_log_normalized',lambda i,r:r['own_line_connect_previous'],colors[0],'Jianping maize')
h.panel_line(ax,rows,'other11_log_normalized',lambda i,r:not r['source_break'] and r['other11_valid']==11 and rows[i-1]['other11_valid']==11,'#777','Other eleven maize median',ls='--')
h.panel_line(ax,rows,'national_log_normalized',lambda i,r:r['national_line_connect_previous'],'#CC79A7','National second-grade yellow maize')
ax.axvline(datetime(2024,2,5),color='#999',ls=':',lw=.9);ax.set_ylabel('Log price relative to own January 2018 mean');ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));h.style_axis(ax)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',frameon=False,ncol=1,fontsize=8.5);fig.tight_layout(rect=(0,.15,1,1));save(fig,'Figure_S2')
h.write_json(OUT/'figure_manifest.json',{'status':'GENERATED_REQUIRES_VISUAL_REVIEW','scientific_resampling':False,'dpi':600,'source_index':ix,'artifacts':records})
print(json.dumps({'status':'GENERATED','figures':4,'formats':'PNG/TIFF/PDF','resampling':False}))
