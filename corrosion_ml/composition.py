"""Statistical composition estimation fitted only on training rows."""
import numpy as np,pandas as pd
from sklearn.base import BaseEstimator,TransformerMixin
from . import data as al
ELEMENTS='C Si Mn P S Cr Ni Mo Cu N'.split()
NUMERIC=al.NUM+al.PROCESS_NUM+[f'original_missing_{c}' for c in ELEMENTS]
CATEGORICAL=al.CAT+al.PROCESS_CAT
class CompositionDonorImputer(BaseEstimator, TransformerMixin):
    def __init__(self, enabled=True):
        self.enabled = enabled

    def fit(self, X, y=None):
        self.training_papers_ = set(X.source_paper_id)
        pool = X[['record_id', 'source_paper_id', 'steel_family']].copy()
        for c in ELEMENTS:
            pool[c] = X['donor_' + c] if 'donor_' + c in X else X[c]
        pool = pool.loc[pool[ELEMENTS].notna().sum(axis=1).ge(3)]
        self.pool_ = pool.drop_duplicates(['source_paper_id'] + ELEMENTS).reset_index(drop=True)
        self.scale_ = (self.pool_[ELEMENTS].quantile(.75)-self.pool_[ELEMENTS].quantile(.25)).replace(0,np.nan).fillna(1)
        return self

    def transform(self, X):
        result = X.copy()
        for c in ELEMENTS:
            if 'original_missing_' + c not in result:
                result['original_missing_' + c] = result[c].isna().astype(int)
        if self.enabled:
            # Freeze each row before estimating: inferred elements never cascade.
            for i,row in X.iterrows():
                pool = self.pool_.loc[self.pool_.steel_family.eq(row.steel_family)].copy()
                if 'source_paper_id' in X:
                    pool = pool.loc[pool.source_paper_id.ne(row.source_paper_id)]
                if pd.notna(row.Cr):
                    pool = pool.loc[pool.Cr.notna() & pool.Cr.ge(10).eq(row.Cr >= 10)]
                if pd.notna(row.Ni) and row.Ni >= 6:
                    pool = pool.loc[pool.Ni.ge(6)]
                overlap = pool[ELEMENTS].notna() & row[ELEMENTS].notna()
                count = overlap.sum(axis=1)
                distance = ((pool[ELEMENTS]-row[ELEMENTS])/self.scale_).abs().where(overlap).mean(axis=1)
                pool = pool.assign(distance=distance).loc[count.ge(2)].sort_values('distance',kind='stable')
                for c in ELEMENTS:
                    if pd.notna(row[c]): continue
                    donors = pool.loc[pool[c].notna()].drop_duplicates('source_paper_id').head(5)
                    if len(donors)<3: continue
                    value = float(donors[c].median())
                    bound = c + '_upper_bound_wt_pct'
                    if bound in X and pd.notna(row[bound]):
                        value = min(value, float(row[bound])*.5)
                    result.at[i,c] = value
        for c in CATEGORICAL:
            result[c] = result[c].fillna('missing').astype(str)
        return result
