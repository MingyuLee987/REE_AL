import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import active_learning as al
import curate_data as cd


class CurationTests(unittest.TestCase):
    def test_source_rules_provenance_and_target_preservation(self):
        d = pd.DataFrame({c: [0.1] * 4 for c in al.NUM})
        for c in al.CAT:
            d[c] = ['known'] * 4
        d['record_id'] = ['r0', 'r1', 'r2', 'r3']
        d['source_paper_id'] = ['10.1038/s41598-024-67799-9',
                                '10.1038/s41529-025-00682-8',
                                '10.1007/s11663-025-03817-z',
                                'unreviewed']
        d['source_sample_id'] = ['C1', '0La_25C_8d', 'S2_1180C_60min', 'other']
        d['phase_source_url'] = 'https://example.org/unreviewed'
        d[al.TARGET] = [1e-4, 2.476e-7, 1.563e-7, 1e-6]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.bin'
            source.write_bytes(b'immutable-test-source')
            with patch.object(cd, 'ROOT', root / 'audit'), patch.object(cd, 'DATA', root / 'data'), patch.object(cd.pd, 'read_excel', return_value=d.copy()):
                curated = cd.build(source)
            pd.testing.assert_series_equal(curated[al.TARGET], d[al.TARGET])
            self.assertEqual(curated.loc[0, 'exposure_h'], 960.)
            self.assertTrue(np.isnan(curated.loc[1, 'pH']))
            self.assertEqual(curated.loc[1, 'pH_lower_bound'], 14.)
            self.assertTrue(np.isnan(curated.loc[1, 'scan_rate_mV_s']))
            self.assertEqual(curated.loc[2, 'heat_treatment_temperature_C'], 1180.)
            self.assertEqual(curated.loc[2, 'heat_treatment_time_min'], 60.)
            self.assertEqual(curated.loc[2, 'temperature_C'], .1)
            pd.testing.assert_series_equal(curated.loc[3, al.NUM], d.loc[3, al.NUM])
            changes = pd.read_csv(root / 'audit/changes.csv')
            self.assertTrue(changes[['record_id', 'source_url', 'locator', 'reason']].notna().all().all())
            self.assertNotIn(al.TARGET, changes.column.tolist())
            restored = al.load(root / 'data/curated_corrosion.csv')
            np.testing.assert_array_equal(restored[al.TARGET], d[al.TARGET])
            x, nums, cats = al.features(curated, process=True)
            self.assertNotIn('target_review_status', nums + cats)
            self.assertNotIn('source_paper_id', nums + cats)
            self.assertIn('heat_treatment_temperature_C', x.columns)


if __name__ == '__main__':
    unittest.main()
