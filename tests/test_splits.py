import unittest
import numpy as np
import pandas as pd
from corrosion_ml.data import validation_splits

class RandomValidationTests(unittest.TestCase):
    def test_random_splits_are_reproducible_and_cover_each_row_once(self):
        d=pd.DataFrame({'source_paper_id':['a','b']*20})
        first=list(validation_splits(d,5,'random'));second=list(validation_splits(d,5,'random'))
        for (tr,te),(tr2,te2) in zip(first,second):
            self.assertFalse(set(tr)&set(te))
            np.testing.assert_array_equal(te,te2)
            np.testing.assert_array_equal(tr,tr2)
            self.assertTrue(set(d.iloc[tr].source_paper_id)&set(d.iloc[te].source_paper_id))
        np.testing.assert_array_equal(np.sort(np.concatenate([te for tr,te in first])),np.arange(len(d)))

    def test_paper_mode_remains_available(self):
        d=pd.DataFrame({'source_paper_id':np.repeat(['a','b','c','d','e'],4)})
        for tr,te in validation_splits(d,5,'paper'):
            self.assertFalse(set(d.iloc[tr].source_paper_id)&set(d.iloc[te].source_paper_id))

if __name__=='__main__':unittest.main()
