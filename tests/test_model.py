import tempfile,unittest
from pathlib import Path
import joblib,numpy as np
import pandas as pd
from sklearn.svm import SVR
from corrosion_ml.model import BootstrapSVR
from corrosion_ml.active_learning import query

class BootstrapTests(unittest.TestCase):
    def test_acquisition_rejects_hidden_target_column(self):
        pool=pd.DataFrame({'record_id':['candidate'],'icorr_A_cm2':[1e-6]})
        with self.assertRaises(ValueError):query(None,None,[],pool,1,'uncertainty',np.random.default_rng(42))

    def test_central_prediction_matches_fixed_svr_and_bootstrap_reloads(self):
        rng=np.random.default_rng(42);x=rng.normal(size=(30,4));y=x[:,0]+.2*rng.normal(size=30)
        model=BootstrapSVR(n_members=4,seed=42).fit(x,y)
        np.testing.assert_allclose(model.predict(x),SVR(C=10.,epsilon=.15).fit(x,y).predict(x))
        self.assertTrue(np.isfinite(model.uncertainty(x)).all())
        self.assertTrue(np.all(model.uncertainty(x)>=0))
        for indices in model.bootstrap_indices_:self.assertTrue(set(indices).issubset(range(len(y))))
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'committee.joblib';joblib.dump(model,path);loaded=joblib.load(path)
            np.testing.assert_allclose(loaded.uncertainty(x),model.uncertainty(x))

    def test_bootstrap_seed_is_reproducible(self):
        rng=np.random.default_rng(42);x=rng.normal(size=(20,3));y=rng.normal(size=20)
        a=BootstrapSVR(n_members=3,seed=7).fit(x,y);b=BootstrapSVR(n_members=3,seed=7).fit(x,y)
        np.testing.assert_allclose(a.uncertainty(x),b.uncertainty(x))
        with self.assertRaises(ValueError):BootstrapSVR(n_members=1).fit(x,y)

if __name__=='__main__':unittest.main()
