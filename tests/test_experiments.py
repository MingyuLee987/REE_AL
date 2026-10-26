import unittest
import numpy as np,pandas as pd
from corrosion_ml import data as al
from corrosion_ml.experiments import metrics,validate_phases,predict_without_target

class ExperimentalValidationTests(unittest.TestCase):
    def test_metrics_report_constant_or_singleton_r2_as_undefined(self):
        self.assertIsNone(metrics([-6],[-5.7])['r2_log10'])
        self.assertIsNone(metrics([-6,-6],[-5.9,-6.1])['r2_log10'])
        self.assertAlmostEqual(metrics([-6,-5],[-5,-4])['geometric_mean_fold_error'],10.)

    def test_missing_phases_stay_missing_and_invalid_sums_rejected(self):
        x,total=validate_phases(pd.DataFrame({'ferrite_fraction_pct':[60.,np.nan],'martensite_fraction_pct':[40.,np.nan]}))
        self.assertEqual(total.iloc[0],100.)
        self.assertTrue(np.isnan(total.iloc[1]))
        with self.assertRaises(ValueError):validate_phases(pd.DataFrame({'ferrite_fraction_pct':[80.],'martensite_fraction_pct':[40.]}))

    def test_measured_target_never_passes_to_model(self):
        d=pd.DataFrame({c:[.1,.2] for c in al.NUM+al.PROCESS_NUM})
        for c in al.CAT+al.PROCESS_CAT:d[c]='known'
        d[al.TARGET]=[1e-6,1e-5]
        class Dummy:
            def predict(self,x):
                assert al.TARGET not in x
                return np.array([-6.,-5.])
        np.testing.assert_array_equal(predict_without_target(Dummy(),d),[-6.,-5.])

if __name__=='__main__':unittest.main()
