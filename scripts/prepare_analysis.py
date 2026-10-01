"""Extract sector totals and calculate simple NDC pathway diagnostics."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "final-greenhouse-gas-emissions-tables-2024.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "tables"
EXPECTED_SHA256 = "39849813643d6ed812c10030fb4fdcba98e598d7f8a890a446450c74baba66fa"
TARGETS = {2030: 0.68, 2035: 0.81}
PACE_PERIODS = ((1990, 2000), (2000, 2010), (2010, 2020), (2020, 2024), (2014, 2024))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sector_totals(workbook_path: Path) -> tuple[list[dict[str, float | str]], dict[int, float]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["1.2"]
    if sheet["A5"].value != "Geographical coverage of table: United Kingdom.":
        raise ValueError("Table 1.2 is not labelled as United Kingdom coverage")

    years = {
        int(sheet.cell(6, column).value): column
        for column in range(4, sheet.max_column + 1)
        if sheet.cell(6, column).value is not None
    }
    required_years = {1990, 2024}
    if not required_years.issubset(years):
        raise ValueError("Table 1.2 does not contain both 1990 and 2024")

    totals: list[dict[str, float | str]] = []
    grand_total: dict[int, float] = {}
    for row in range(7, sheet.max_row + 1):
        label = sheet.cell(row, 1).value
        if label == "Grand total":
            grand_total = {year: float(sheet.cell(row, years[year]).value) for year in required_years}
        elif isinstance(label, str) and label.endswith(" total"):
            sector = label.removesuffix(" total")
            start = float(sheet.cell(row, years[1990]).value)
            end = float(sheet.cell(row, years[2024]).value)
            totals.append(
                {
                    "sector": sector,
                    "emissions_1990_mtco2e": start,
                    "emissions_2024_mtco2e": end,
                    "change_mtco2e": end - start,
                    "avoided_emissions_mtco2e": start - end,
                }
            )

    if len(totals) != 8 or set(grand_total) != required_years:
        raise ValueError("Expected eight TES sector totals and a grand total")

    net_reduction = grand_total[1990] - grand_total[2024]
    for record in totals:
        record["share_of_net_reduction"] = float(record["avoided_emissions_mtco2e"]) / net_reduction
    return totals, grand_total


def load_sector_context(workbook_path: Path) -> list[dict[str, float | str]]:
    """Extract selected sector years for recent-change interpretation."""
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["1.2"]
    years = {
        int(sheet.cell(6, column).value): column
        for column in range(4, sheet.max_column + 1)
        if sheet.cell(6, column).value is not None
    }
    selected_years = (1990, 2014, 2019, 2024)
    if not set(selected_years).issubset(years):
        raise ValueError("Table 1.2 is missing a required comparison year")

    records: list[dict[str, float | str]] = []
    grand_2024 = None
    for row in range(7, sheet.max_row + 1):
        label = sheet.cell(row, 1).value
        if label == "Grand total":
            grand_2024 = float(sheet.cell(row, years[2024]).value)
        elif isinstance(label, str) and label.endswith(" total"):
            values = {year: float(sheet.cell(row, years[year]).value) for year in selected_years}
            records.append(
                {
                    "sector": label.removesuffix(" total"),
                    **{f"emissions_{year}_mtco2e": value for year, value in values.items()},
                    "reduction_2014_2024_mtco2e": values[2014] - values[2024],
                    "mean_annual_reduction_2014_2024_mtco2e": (values[2014] - values[2024]) / 10,
                    "reduction_2019_2024_mtco2e": values[2019] - values[2024],
                }
            )
    if grand_2024 is None or len(records) != 8:
        raise ValueError("Expected eight sectors and a 2024 grand total")
    for record in records:
        record["share_of_2024_emissions"] = float(record["emissions_2024_mtco2e"]) / grand_2024
    return records


def load_ndc_inputs(workbook_path: Path) -> dict[str, float]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["2.2"]
    coverage = str(sheet["A10"].value)
    if "UK" not in coverage or "Gibraltar" not in coverage:
        raise ValueError("Unexpected geographical coverage in Table 2.2")

    headers = {sheet.cell(11, column).value: column for column in range(2, 13)}
    base = float(sheet.cell(12, headers["Base year"]).value)
    observations = {
        int(year): float(sheet.cell(12, headers[year]).value)
        for year in ("2021", "2022", "2023", "2024")
    }
    emissions_2024 = observations[2024]
    published_2030_target = float(sheet.cell(15, headers["2030"]).value)
    result = {
        "base_year_mtco2e": base,
        "emissions_2024_mtco2e": emissions_2024,
        "published_2030_target_mtco2e": published_2030_target,
    }
    result.update({f"emissions_{year}_mtco2e": value for year, value in observations.items()})
    return result


def load_ndc_timeseries(workbook_path: Path) -> dict[int, float]:
    """Read the complete Paris Agreement reporting-scope series from Table 3.3."""
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["3.3"]
    if "Paris Agreement" not in str(sheet["A6"].value) or "Gibraltar" not in str(sheet["A6"].value):
        raise ValueError("Unexpected Paris Agreement scope note in Table 3.3")
    if sheet["A16"].value != "Total greenhouse gas emissions reported under the Paris Agreement":
        raise ValueError("Paris Agreement total row was not found in Table 3.3")
    return {
        int(sheet.cell(9, column).value): float(sheet.cell(16, column).value)
        for column in range(2, sheet.max_column + 1)
        if sheet.cell(9, column).value is not None
    }


def load_sector_uncertainty(workbook_path: Path) -> list[dict[str, float | str]]:
    """Read published 2024 uncertainty intervals from DESNZ Table 4.2.

    These values cover the UK, Crown Dependencies and relevant Overseas
    Territories. They are kept separate from the UK-only Table 1.2 values.
    """
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["4.2"]
    coverage = str(sheet["A9"].value)
    if "Crown Dependencies" not in coverage or "Overseas Territories" not in coverage:
        raise ValueError("Unexpected geographical coverage in Table 4.2")

    rows: list[dict[str, float | str]] = []
    for row in range(11, 20):
        rows.append(
            {
                "sector": str(sheet.cell(row, 1).value),
                "emissions_2024_mtco2e": float(sheet.cell(row, 3).value),
                "uncertainty_fraction": float(sheet.cell(row, 4).value),
                "lower_95_mtco2e": float(sheet.cell(row, 5).value),
                "upper_95_mtco2e": float(sheet.cell(row, 6).value),
                "change_1990_2024_fraction": float(sheet.cell(row, 7).value),
                "change_lower_95_fraction": float(sheet.cell(row, 8).value),
                "change_upper_95_fraction": float(sheet.cell(row, 9).value),
            }
        )
    return rows


def calculate_pathways(base: float, emissions_2024: float) -> list[dict[str, float | int]]:
    pathways: list[dict[str, float | int]] = []
    for target_year, reduction_fraction in TARGETS.items():
        years = target_year - 2024
        target = base * (1 - reduction_fraction)
        gap = emissions_2024 - target
        pathways.append(
            {
                "target_year": target_year,
                "target_reduction_fraction": reduction_fraction,
                "target_emissions_mtco2e": target,
                "remaining_gap_from_2024_mtco2e": gap,
                "constant_absolute_reduction_mtco2e_per_year": gap / years,
                "constant_percentage_reduction_per_year": 1 - math.pow(target / emissions_2024, 1 / years),
            }
        )
    return pathways


def calculate_historical_pace(timeseries: dict[int, float]) -> list[dict[str, float | int | str]]:
    years = sorted(timeseries)
    rows: list[dict[str, float | int | str]] = []
    for year in years:
        if year == years[0]:
            annual_reduction: float | str = ""
        else:
            annual_reduction = timeseries[year - 1] - timeseries[year]
        trailing_start = year - 5
        trailing_mean: float | str = ""
        if trailing_start in timeseries:
            trailing_mean = (timeseries[trailing_start] - timeseries[year]) / 5
        rows.append(
            {
                "year": year,
                "emissions_mtco2e": timeseries[year],
                "annual_reduction_mtco2e": annual_reduction,
                "trailing_5y_mean_reduction_mtco2e_per_year": trailing_mean,
            }
        )
    return rows


def calculate_period_pace(
    timeseries: dict[int, float], pathways: list[dict[str, float | int]]
) -> list[dict[str, float | int | str]]:
    required_2030 = float(pathways[0]["constant_absolute_reduction_mtco2e_per_year"])
    required_2035 = float(pathways[1]["constant_absolute_reduction_mtco2e_per_year"])
    rows: list[dict[str, float | int | str]] = []
    for start, end in PACE_PERIODS:
        years = end - start
        absolute = (timeseries[start] - timeseries[end]) / years
        compound = 1 - math.pow(timeseries[end] / timeseries[start], 1 / years)
        rows.append(
            {
                "period": f"{start}-{end}",
                "start_year": start,
                "end_year": end,
                "mean_absolute_reduction_mtco2e_per_year": absolute,
                "compound_reduction_fraction_per_year": compound,
                "ratio_to_required_2030_absolute_pace": absolute / required_2030,
                "ratio_to_required_2035_absolute_pace": absolute / required_2035,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if sha256(SOURCE_PATH) != EXPECTED_SHA256:
        raise ValueError("Source workbook checksum does not match the reviewed file")

    sectors, grand_total = load_sector_totals(SOURCE_PATH)
    sector_sum_1990 = sum(float(row["emissions_1990_mtco2e"]) for row in sectors)
    sector_sum_2024 = sum(float(row["emissions_2024_mtco2e"]) for row in sectors)
    if not math.isclose(sector_sum_1990, grand_total[1990], abs_tol=1e-9):
        raise ValueError("1990 sector totals do not reconcile to the grand total")
    if not math.isclose(sector_sum_2024, grand_total[2024], abs_tol=1e-9):
        raise ValueError("2024 sector totals do not reconcile to the grand total")

    ndc = load_ndc_inputs(SOURCE_PATH)
    pathways = calculate_pathways(ndc["base_year_mtco2e"], ndc["emissions_2024_mtco2e"])
    if not math.isclose(
        float(pathways[0]["target_emissions_mtco2e"]),
        ndc["published_2030_target_mtco2e"],
        abs_tol=1e-9,
    ):
        raise ValueError("Calculated 2030 target does not match Table 2.2")

    uncertainty = load_sector_uncertainty(SOURCE_PATH)
    for record in uncertainty:
        central = float(record["emissions_2024_mtco2e"])
        lower = float(record["lower_95_mtco2e"])
        upper = float(record["upper_95_mtco2e"])
        if not lower <= central <= upper:
            raise ValueError(f"Uncertainty interval does not contain central estimate for {record['sector']}")

    observations = [
        {"year": year, "emissions_mtco2e": ndc[f"emissions_{year}_mtco2e"]}
        for year in range(2021, 2025)
    ]
    ndc_timeseries = load_ndc_timeseries(SOURCE_PATH)
    for year in range(2021, 2025):
        if not math.isclose(ndc_timeseries[year], ndc[f"emissions_{year}_mtco2e"], abs_tol=1e-9):
            raise ValueError(f"Table 3.3 does not match Table 2.2 for {year}")
    historical_pace = calculate_historical_pace(ndc_timeseries)
    period_pace = calculate_period_pace(ndc_timeseries, pathways)
    sector_context = load_sector_context(SOURCE_PATH)

    write_csv(OUTPUT_DIR / "sector_change_1990_2024.csv", sectors)
    write_csv(OUTPUT_DIR / "sector_context.csv", sector_context)
    write_csv(OUTPUT_DIR / "sector_uncertainty_2024.csv", uncertainty)
    write_csv(OUTPUT_DIR / "ndc_observations_2021_2024.csv", observations)
    write_csv(OUTPUT_DIR / "ndc_pathway_diagnostics.csv", pathways)
    write_csv(OUTPUT_DIR / "ndc_historical_pace.csv", historical_pace)
    write_csv(OUTPUT_DIR / "period_pace_comparison.csv", period_pace)


if __name__ == "__main__":
    main()

