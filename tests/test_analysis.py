import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from prepare_analysis import (
    SOURCE_PATH,
    calculate_pathways,
    calculate_historical_pace,
    calculate_period_pace,
    load_ndc_inputs,
    load_ndc_timeseries,
    load_sector_context,
    load_sector_totals,
    load_sector_uncertainty,
)


class AnalysisTests(unittest.TestCase):
    def test_sector_totals_reconcile(self) -> None:
        sectors, grand_total = load_sector_totals(SOURCE_PATH)
        self.assertEqual(len(sectors), 8)
        for year in (1990, 2024):
            field = f"emissions_{year}_mtco2e"
            self.assertTrue(
                math.isclose(
                    sum(float(row[field]) for row in sectors),
                    grand_total[year],
                    abs_tol=1e-9,
                )
            )

    def test_2030_target_matches_published_value(self) -> None:
        ndc = load_ndc_inputs(SOURCE_PATH)
        pathways = calculate_pathways(ndc["base_year_mtco2e"], ndc["emissions_2024_mtco2e"])
        target_2030 = next(row for row in pathways if row["target_year"] == 2030)
        self.assertTrue(
            math.isclose(
                float(target_2030["target_emissions_mtco2e"]),
                ndc["published_2030_target_mtco2e"],
                abs_tol=1e-9,
            )
        )

    def test_pathway_rates_are_positive(self) -> None:
        ndc = load_ndc_inputs(SOURCE_PATH)
        pathways = calculate_pathways(ndc["base_year_mtco2e"], ndc["emissions_2024_mtco2e"])
        for row in pathways:
            self.assertGreater(float(row["constant_absolute_reduction_mtco2e_per_year"]), 0)
            self.assertGreater(float(row["constant_percentage_reduction_per_year"]), 0)

    def test_uncertainty_intervals_contain_central_estimates(self) -> None:
        rows = load_sector_uncertainty(SOURCE_PATH)
        self.assertEqual(len(rows), 9)
        for row in rows:
            self.assertLessEqual(float(row["lower_95_mtco2e"]), float(row["emissions_2024_mtco2e"]))
            self.assertGreaterEqual(float(row["upper_95_mtco2e"]), float(row["emissions_2024_mtco2e"]))

    def test_ndc_observation_years_are_complete(self) -> None:
        ndc = load_ndc_inputs(SOURCE_PATH)
        for year in range(2021, 2025):
            self.assertIn(f"emissions_{year}_mtco2e", ndc)

    def test_full_ndc_series_matches_recent_observations(self) -> None:
        ndc = load_ndc_inputs(SOURCE_PATH)
        series = load_ndc_timeseries(SOURCE_PATH)
        self.assertEqual(len(series), 35)
        self.assertEqual((min(series), max(series)), (1990, 2024))
        for year in range(2021, 2025):
            self.assertTrue(math.isclose(series[year], ndc[f"emissions_{year}_mtco2e"], abs_tol=1e-9))

    def test_annual_reductions_reconcile_to_total_change(self) -> None:
        series = load_ndc_timeseries(SOURCE_PATH)
        rows = calculate_historical_pace(series)
        annual_total = sum(float(row["annual_reduction_mtco2e"]) for row in rows[1:])
        self.assertTrue(math.isclose(annual_total, series[1990] - series[2024], abs_tol=1e-9))

    def test_period_pace_uses_reviewed_endpoints(self) -> None:
        ndc = load_ndc_inputs(SOURCE_PATH)
        pathways = calculate_pathways(ndc["base_year_mtco2e"], ndc["emissions_2024_mtco2e"])
        periods = calculate_period_pace(load_ndc_timeseries(SOURCE_PATH), pathways)
        recent_decade = next(row for row in periods if row["period"] == "2014-2024")
        self.assertTrue(
            math.isclose(float(recent_decade["mean_absolute_reduction_mtco2e_per_year"]), 15.806269091761646)
        )

    def test_sector_context_has_eight_sectors(self) -> None:
        rows = load_sector_context(SOURCE_PATH)
        self.assertEqual(len(rows), 8)
        self.assertTrue(math.isclose(sum(float(row["share_of_2024_emissions"]) for row in rows), 1.0))


if __name__ == "__main__":
    unittest.main()

