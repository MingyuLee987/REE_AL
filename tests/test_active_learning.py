import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd

import active_learning as al


class WorkflowTests(unittest.TestCase):
    def data(self):
        rng = np.random.default_rng(5)
        d = pd.DataFrame({c: rng.uniform(0, 1, 24) for c in al.NUM})
        for c in al.CAT:
            d[c] = ['a', 'b'] * 12
        d['record_id'] = [f'r{i}' for i in range(24)]
        d['source_paper_id'] = np.repeat([f'p{i}' for i in range(6)], 4)
        d[al.TARGET] = 10 ** (-5 + d.RE_ppm)
        d['N'] = np.nan
        return d

    def args(self):
        return Namespace(with_phase=False, seeds=[42], initial=6, rounds=1,
                         batch_size=2, beta=1., strategy='uncertainty', sheet='ENRICHED_DATA')

    def test_invalid_labels(self):
        d = self.data()
        for value in [0, -1, np.nan, np.inf]:
            d.loc[0, al.TARGET] = value
            with self.assertRaises(ValueError):
                al.labels(d)

    def test_simulation_groups_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            al.simulate(self.data(), self.args(), out)
            splits = pd.read_csv(out / 'splits.csv')
            test = set(splits.loc[splits.partition == 'test', 'source_paper_id'])
            train = set(splits.loc[splits.partition != 'test', 'source_paper_id'])
            self.assertFalse(test & train)
            curves = pd.read_csv(out / 'learning_curves.csv')
            self.assertEqual(set(curves.n_labeled), {6, 8})
            for col in ['mae_log10', 'rmse_log10', 'r2_log10']:
                self.assertEqual(curves[curves['round'] == 0][col].nunique(), 1)
            queries = pd.read_csv(out / 'queries.csv')
            self.assertFalse(set(queries.record_id) & set(splits.loc[splits.partition == 'test', 'record_id']))

    def test_recommend_deduplicates_and_rejects_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            d = self.data()
            c = d.iloc[:3].drop(columns=[al.TARGET]).copy()
            c.record_id = ['new0', 'new1', 'new2']
            c.loc[1, 'RE_ppm'] = 2.
            c.loc[2, al.NUM + al.CAT] = c.loc[1, al.NUM + al.CAT].values
            args = self.args()
            args.candidates = out / 'candidates.csv'
            c.to_csv(args.candidates, index=False)
            al.recommend(d, args, out)
            result = pd.read_csv(out / 'next_batch.csv')
            self.assertEqual(result.record_id.tolist(), ['new1'])
            self.assertTrue(np.isfinite(result.pred_log10_icorr).all())
            c[al.TARGET] = 1.
            c.to_csv(args.candidates, index=False)
            with self.assertRaises(ValueError):
                al.recommend(d, args, out)


if __name__ == '__main__':
    unittest.main()
