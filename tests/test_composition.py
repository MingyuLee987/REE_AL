import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from corrosion_ml.composition import CompositionDonorImputer,ELEMENTS,CATEGORICAL
from corrosion_ml.data import training_data


class TrainOnlyImputationTests(unittest.TestCase):
    def donors(self):
        d=pd.DataFrame({c:[.1,.2,.3] for c in ELEMENTS})
        d['C']=[.10,.11,.12];d['Si']=.2;d['Mn']=.8;d['Cr']=.3
        d['steel_family']='steel';d['record_id']=['a','b','c'];d['source_paper_id']=['p1','p2','p3']
        for c in CATEGORICAL:
            if c not in d:d[c]='known'
        return d

    def test_heldout_values_and_target_cannot_change_fitted_donors(self):
        train=self.donors()
        imputer=CompositionDonorImputer().fit(train,np.array([1,2,3]))
        test=train.iloc[:1].copy();test['source_paper_id']='unseen';test['Ni']=np.nan
        before=imputer.transform(test)
        contaminated=test.copy();contaminated['Ni']=99
        together=pd.concat([test,contaminated],ignore_index=True)
        after=imputer.transform(together)
        self.assertAlmostEqual(before.Ni.iloc[0],.2)
        self.assertEqual(after.Ni.iloc[0],before.Ni.iloc[0])
        self.assertEqual(after.Ni.iloc[1],99)
        self.assertNotIn('unseen',imputer.training_papers_)
        other=CompositionDonorImputer().fit(train,np.array([100,200,300]))
        pd.testing.assert_frame_equal(before,other.transform(test))

    def test_insufficient_distinct_papers_keeps_missing(self):
        train=self.donors();train['source_paper_id']=['same','same','another']
        imputer=CompositionDonorImputer().fit(train)
        test=train.iloc[:1].copy();test['source_paper_id']='unseen';test['Ni']=np.nan
        self.assertTrue(np.isnan(imputer.transform(test).Ni.iloc[0]))

    def test_exported_statistical_estimates_are_reverted(self):
        d=training_data()
        self.assertEqual(len(d),279)
        self.assertNotIn('10.1007/s11003-015-9767-2',set(d.source_paper_id))
        log=pd.read_csv(Path(__file__).resolve().parents[1]/'data/provenance/estimation_log.csv')
        d=d.set_index('record_id')
        for row in log.loc[log.method.eq('cross_paper_similar_alloy_median')].itertuples():
            if row.record_id in d.index:self.assertTrue(pd.isna(d.at[row.record_id,row.element]))


if __name__=='__main__':
    unittest.main()
