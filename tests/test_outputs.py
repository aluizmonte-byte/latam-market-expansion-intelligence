import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ranking = pd.read_csv(ROOT / "data" / "processed" / "market_opportunity_ranking.csv")
        cls.sensitivity = pd.read_csv(ROOT / "data" / "processed" / "weight_sensitivity.csv")

    def test_complete_country_set(self):
        self.assertEqual(len(self.ranking), 10)
        self.assertEqual(self.ranking["country"].nunique(), 10)

    def test_scores_are_bounded_and_ranks_unique(self):
        self.assertTrue(self.ranking["opportunity_score"].between(0, 100).all())
        self.assertEqual(set(self.ranking["rank"]), set(range(1, 11)))

    def test_sensitivity_probabilities_are_bounded(self):
        self.assertTrue(self.sensitivity["top3_probability"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
