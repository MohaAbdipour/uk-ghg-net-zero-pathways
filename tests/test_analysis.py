import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from prepare_analysis import SOURCE_PATH, calculate_pathways, load_ndc_inputs, load_sector_totals


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


if __name__ == "__main__":
    unittest.main()

