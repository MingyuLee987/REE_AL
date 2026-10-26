"""Plot completed, matched-budget random-row AL results."""
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    root=Path(__file__).resolve().parent.parent/'results/active_learning'
    s=pd.read_csv(root/'summary.csv');curves=pd.read_csv(root/'learning_curves.csv')
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.7))
    labels={'random':'Random','uncertainty':'Bootstrap uncertainty','diverse_uncertainty':'Uncertainty + diversity'}
    colors={'random':'#777777','uncertainty':'#bd7235','diverse_uncertainty':'#24679c'}
    for strategy,g in s.groupby('strategy'):
        axes[0].errorbar(g.fraction*100,g.mean_r2,yerr=g.std_r2,marker='o',capsize=3,label=labels[strategy],color=colors[strategy])
    axes[0].set_xlabel('Labeled fraction of training pool (%)');axes[0].set_ylabel('Mean held-out test R2 (log10 i_corr)')
    axes[0].set_title('Same fixed SVR, same row budget');axes[0].legend(fontsize=8)
    per=curves.groupby(['strategy','stage','fold']).r2_log10.mean().unstack('strategy')
    xs=np.arange(2);width=.34
    for j,strategy in enumerate(['uncertainty','diverse_uncertainty']):
        means=[];stds=[]
        for stage in [1,2]:
            delta=per.loc[stage,strategy]-per.loc[stage,'random'];means.append(delta.mean());stds.append(delta.std())
        axes[1].bar(xs+(j-.5)*width,means,width,yerr=stds,capsize=3,label=labels[strategy],color=colors[strategy])
    axes[1].axhline(0,color='black',linewidth=.7);axes[1].set_xticks(xs,['50% labeled','75% labeled'])
    axes[1].set_ylabel('Paired test R2 difference vs random');axes[1].set_title('Error bars: fold standard deviation');axes[1].legend(fontsize=8)
    fig.suptitle('Retrospective random-row CV: 5 folds, 2 starts, batches of 10; 15 bootstrap SVRs',fontsize=10)
    fig.tight_layout();fig.savefig(root/'learning_curves.png',dpi=180)
    auc=[]
    for (fold,seed,strategy),g in curves.groupby(['fold','seed','strategy']):
        g=g.sort_values('fraction');auc.append(dict(fold=int(fold),seed=int(seed),strategy=strategy,normalized_area=float(np.trapezoid(g.r2_log10,g.fraction)/.75)))
    pd.DataFrame(auc).to_csv(root/'curve_area.csv',index=False)
    print('Saved learning_curves.png and curve_area.csv')

if __name__=='__main__':main()
