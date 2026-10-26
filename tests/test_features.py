import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from corrosion_ml.features import parse_medium,CorrosionFeatures
from corrosion_ml.data import training_data


class CorrosionFeatureTests(unittest.TestCase):
    def test_equivalent_names_preserve_percent_basis_and_do_not_invent_molarity(self):
        a=parse_medium('NaCl_3.5wtpct');b=parse_medium('3.5 wt.% NaCl')
        self.assertEqual(a,b)
        self.assertTrue(np.isnan(a['quantified_chloride_mol_L']))
        self.assertEqual(parse_medium('NaCl_3.5pct')['nacl_percent_basis'],'unspecified_percent')
        self.assertTrue(np.isnan(parse_medium('natural_seawater')['quantified_chloride_mol_L']))

    def test_prefix_mixture_maps_each_concentration_to_its_own_salt(self):
        p=parse_medium('pore_solution_10mM_Na2SO4_0.4M_KOH_1mM_CaOH2_0.6M_NaCl')
        self.assertAlmostEqual(p['quantified_sulfate_mol_L'],.01)
        self.assertAlmostEqual(p['added_strong_base_mol_L'],.4)
        self.assertAlmostEqual(p['quantified_chloride_mol_L'],.6)

    def test_postfix_mixture_and_mass_concentrations(self):
        p=parse_medium('soil_CaCl2_0.056gL_NaCl_0.234gL_Na2SO4_0.071gL_MgSO4_0.039gL')
        self.assertAlmostEqual(p['nacl_g_L'],.234)
        self.assertAlmostEqual(p['cacl2_g_L'],.056)
        self.assertAlmostEqual(p['na2so4_g_L'],.071)
        self.assertAlmostEqual(p['quantified_chloride_mol_L'],.234/58.44)
        self.assertTrue(np.isnan(p['cacl2_mol_L']))
        p=parse_medium('seawater+NaOH_40gL+Na2SO4_7.1gL')
        self.assertAlmostEqual(p['added_strong_base_mol_L'],1.)
        self.assertAlmostEqual(p['na2so4_g_L'],7.1)
        self.assertAlmostEqual(parse_medium('HCl_0.1mol_L')['quantified_chloride_mol_L'],.1)

    def test_target_and_identifiers_do_not_enter_features(self):
        d=training_data();a=d.copy()
        a['icorr_A_cm2']=1.;a['source_paper_id']='changed';a['record_id']='changed'
        from corrosion_ml.composition import CompositionDonorImputer
        # Feature engineering itself is stateless and outcome-blind.
        fe=CorrosionFeatures('environment')
        x=fe.fit_transform(d);other=fe.fit_transform(a)
        pd.testing.assert_frame_equal(x,other)
        self.assertNotIn('source_paper_id',x)
        self.assertNotIn('icorr_A_cm2',x)


if __name__=='__main__':unittest.main()
