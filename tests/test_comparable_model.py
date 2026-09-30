"""Checks for source fidelity and year-to-year comparability."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_analysis import CORE_KEYS, CORE_WEIGHTS, load_sources, build_current, scale, validate_history


class ComparableModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history, cls.manifest = load_sources()
        cls.panel = pd.read_csv(ROOT / "data/processed/market_screening_panel_2024_2025.csv")
        cls.comparison = pd.read_csv(ROOT / "data/processed/market_screening_comparison_2024_2025.csv")

    def test_values_match_source_without_imputation(self):
        observed = self.panel.melt(id_vars=["year","country_code"], value_vars=list(CORE_KEYS),
                                   var_name="indicator", value_name="output_value")
        joined = observed.merge(self.history[["year","country_code","indicator","value"]],
                                 on=["year","country_code","indicator"], validate="one_to_one")
        self.assertEqual(len(joined), 100)
        self.assertFalse(joined.value.isna().any())
        np.testing.assert_allclose(joined.output_value, joined.value, rtol=1e-12)

    def test_same_calibration_for_both_years(self):
        parameters = json.loads((ROOT / "data/processed/scaling_parameters_2024_2025.json").read_text())
        for key in CORE_KEYS:
            p = parameters[key]
            expected = np.clip((self.panel[key].clip(p["p05"],p["p95"])-p["p05"])/(p["p95"]-p["p05"])*100,0,100)
            np.testing.assert_allclose(self.panel["score_"+key],expected,atol=1e-10)
        self.assertAlmostEqual(sum(CORE_WEIGHTS.values()),1)

    def test_reported_changes_match_same_model_scores(self):
        by_year = self.panel.pivot(index="country_code",columns="year",values="screening_score")
        comp = self.comparison.set_index("country_code").reindex(by_year.index)
        np.testing.assert_allclose(comp.score_change_points,by_year[2025]-by_year[2024],atol=1e-10)
        np.testing.assert_array_equal(comp.rank_change,comp.rank_2024-comp.rank_2025)
        for _,g in self.panel.groupby("year"):
            self.assertEqual(set(g["rank"]),set(range(1,11)))
            self.assertTrue(g.screening_score.between(0,100).all())

    def test_missing_core_observation_stops_build(self):
        broken = self.history.copy()
        broken.loc[broken.year.eq(2025)&broken.country_code.eq("MEX")&broken.indicator.eq("gdp_usd"),"value"]=np.nan
        with self.assertRaisesRegex(ValueError,"100 observations"):
            build_current(broken)

    def test_duplicate_source_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate_history(pd.concat([self.history,self.history.iloc[[0]]],ignore_index=True))

    def test_missing_excluded_metrics_are_not_silently_filled(self):
        coverage = pd.read_csv(ROOT / "data/processed/data_coverage_2024_2025.csv").query("year==2025").set_index("indicator")
        self.assertEqual(coverage.loc["internet_users_pct","available"],0)
        self.assertEqual(coverage.loc["inflation_pct","missing_country_codes"],"ARG")
        self.assertEqual(coverage.loc["trade_pct_gdp","missing_country_codes"],"PAN")
        self.assertFalse(set(["score_internet_users_pct","score_trade_pct_gdp","score_inflation_pct"]) & set(self.panel.columns))

    def test_sensitivity_conserves_three_places_per_scenario(self):
        frame = pd.read_csv(ROOT / "data/processed/weight_sensitivity_2025.csv")
        self.assertTrue(frame.top3_share.between(0,1).all())
        self.assertAlmostEqual(frame.top3_share.sum(),3)
        self.assertTrue((frame.score_p10<=frame.score_p90).all())

    def test_flat_series_is_neutral_and_missing_cannot_score(self):
        np.testing.assert_allclose(scale(pd.Series([3.,3.]),3.,3.),[50.,50.])
        with self.assertRaisesRegex(ValueError,"Missing"):
            scale(pd.Series([1.,np.nan]),0.,2.)

    def test_rebuild_does_not_relabel_source_acquisition(self):
        metadata=json.loads((ROOT / "data/processed/analysis_metadata.json").read_text())
        dates=sorted({v.get("retrieved_on") or v["retrieved_at_utc"][:10] for v in self.manifest["sources"].values()})
        self.assertEqual(metadata["source_retrieval_dates"],dates)
        self.assertEqual(metadata["reference_year"],2025)
        self.assertEqual(metadata["legacy_model"]["reference_year"],2024)


if __name__=="__main__":
    unittest.main()
