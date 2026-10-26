import sys
import unittest
from pathlib import Path
import numpy as np

from corrosion_ml.model import rank_batch


class AcquisitionTests(unittest.TestCase):
    def test_repeated_rows_do_not_multiply_paper_uncertainty(self):
        selected=rank_batch(np.array([[0.]]),['known'],np.array([[1.],[1.],[1.],[2.]]),
                            ['paper_a','paper_a','paper_a','paper_b'],np.array([1.,1.,1.,2.]),
                            2,'uncertainty',np.random.default_rng(42))
        self.assertEqual(selected,['paper_b','paper_a'])

    def test_greedy_batch_updates_coverage_and_keeps_papers_unique(self):
        selected=rank_batch(np.array([[0.]]),['known'],np.array([[1.],[2.],[10.]]),
                            ['a','b','c'],np.ones(3),2,'diverse_uncertainty',np.random.default_rng(42))
        self.assertEqual(selected,['c','b'])
        self.assertEqual(len(set(selected)),2)


if __name__=='__main__':unittest.main()
