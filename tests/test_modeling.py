import unittest

import numpy as np
import pandas as pd

from improve_models import choose_config
from recommend_advanced import bootstrap_indices
from regression_models import build_model, electrolyte_descriptors


class ModelTests(unittest.TestCase):
    def data(self):
        rng = np.random.default_rng(1)
        x = pd.DataFrame({'C': rng.uniform(0, .2, 24), 'RE_ppm': rng.uniform(0, 500, 24), 'electrolyte_condition_cat': ['NaCl_3.5wtpct'] * 24})
        x['all_missing'] = np.nan
        return x

    def test_units_not_assumed(self):
        self.assertEqual(electrolyte_descriptors('NaCl_3.5wtpct')[1], 3.5)
        self.assertEqual(electrolyte_descriptors('3.5 wt.% NaCl')[1], 3.5)
        self.assertTrue(np.isnan(electrolyte_descriptors('3.5% NaCl')[1]))
        self.assertTrue(np.isnan(electrolyte_descriptors('NaCl_concentration_conflict')[1]))
        self.assertEqual(electrolyte_descriptors('NaCl_0.1mol_L')[2], .1)
        self.assertEqual(electrolyte_descriptors('seawater+NaOH_40gL')[0], 'alkaline')

    def test_group_selection_and_fold_local_preprocessing(self):
        x = self.data()
        y = x.C.to_numpy() * 10
        groups = np.repeat(np.arange(6), 4)
        configs = [{'model': 'mean', 'params': {}, 'features': 'basic'}, {'model': 'ridge', 'params': {'alpha': 1.}, 'features': 'physical'}]
        chosen, scores = choose_config(x, y, groups, configs, 1)
        self.assertEqual(chosen, 1)
        self.assertTrue(np.isfinite(scores.cv_rmse_log10).all())
        model = build_model(configs[1], 1).fit(x, y)
        original_mean = model.named_steps['preprocess'].named_transformers_['numeric'].named_steps['simpleimputer'].statistics_.copy()
        external = x.iloc[:2].copy()
        external['C'] = 100.
        external['electrolyte_condition_cat'] = 'unseen'
        self.assertTrue(np.isfinite(model.predict(external)).all())
        np.testing.assert_array_equal(original_mean, model.named_steps['preprocess'].named_transformers_['numeric'].named_steps['simpleimputer'].statistics_)

    def test_bootstrap_preserves_whole_papers(self):
        groups = np.array(['a', 'a', 'b', 'b', 'b', 'c'])
        ids = bootstrap_indices(groups, np.random.default_rng(3))
        for group in np.unique(groups):
            counts = [np.count_nonzero(ids == i) for i in np.flatnonzero(groups == group)]
            self.assertEqual(len(set(counts)), 1)

    def test_optional_vae_missing_and_unseen(self):
        try:
            from vae_regressor import MixedVAERegressor
        except ImportError:
            self.skipTest('Install requirements-vae.txt for VAE tests.')
        x = self.data()
        x.loc[:3, 'C'] = np.nan
        model = MixedVAERegressor(epochs=5, random_state=1).fit(x, np.linspace(-6, -4, len(x)))
        external = x.iloc[:2].copy()
        external['electrolyte_condition_cat'] = 'new'
        self.assertTrue(np.isfinite(model.predict(external)).all())
        self.assertEqual(model.transform(external).shape, (2, 4))
        np.testing.assert_array_equal(model.predict(external), model.predict(external))


if __name__ == '__main__':
    unittest.main()
