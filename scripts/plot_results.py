"""Create lightweight SVG figures from the verified analysis tables."""

from __future__ import annotations

import csv
import html
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from prepare_analysis import OUTPUT_DIR, calculate_pathways, load_ndc_inputs, main as prepare_tables


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
SOURCE_PATH = PROJECT_ROOT / "data" / "raw" / "final-greenhouse-gas-emissions-tables-2024.xlsx"

NAVY = "#17365d"
BLUE = "#2c7fb8"
TEAL = "#1b9e77"
ORANGE = "#d95f02"
GREY = "#5d6770"
LIGHT_GREY = "#d9dee3"
PALE = "#f4f6f7"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def text(
    x: float,
    y: float,
    value: str,
    size: int = 16,
    anchor: str = "start",
    weight: str = "normal",
    fill: str = "#1f2933",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str,
    width: float = 1,
    dash: str | None = None,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'
    )


def write_svg(path: Path, width: int, height: int, elements: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        *elements,
        "</g>",
        "</svg>",
    ]
    path.write_text("\n".join(document), encoding="utf-8")
    render_png(path, path.with_suffix(".png"), width, height)


def render_png(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    """Render this project's simple SVG primitives for preview and GitHub use."""
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    regular_path = Path("C:/Windows/Fonts/arial.ttf")
    bold_path = Path("C:/Windows/Fonts/arialbd.ttf")

    def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidate = bold_path if bold else regular_path
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
        return ImageFont.load_default()

    root = ET.parse(svg_path).getroot()
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            x = float(node.attrib.get("x", 0))
            y = float(node.attrib.get("y", 0))
            w = width if node.attrib.get("width") == "100%" else float(node.attrib.get("width", 0))
            h = height if node.attrib.get("height") == "100%" else float(node.attrib.get("height", 0))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=float(node.attrib.get("rx", 0)), fill=node.attrib.get("fill", "white"))
        elif tag == "line":
            draw.line(
                (
                    float(node.attrib["x1"]),
                    float(node.attrib["y1"]),
                    float(node.attrib["x2"]),
                    float(node.attrib["y2"]),
                ),
                fill=node.attrib.get("stroke", "black"),
                width=max(1, round(float(node.attrib.get("stroke-width", 1)))),
            )
        elif tag == "circle":
            cx = float(node.attrib["cx"])
            cy = float(node.attrib["cy"])
            radius = float(node.attrib["r"])
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=node.attrib.get("fill", "black"))
        elif tag == "polyline":
            points = [tuple(map(float, pair.split(","))) for pair in node.attrib["points"].split()]
            draw.line(points, fill=node.attrib.get("stroke", "black"), width=max(1, round(float(node.attrib.get("stroke-width", 1)))), joint="curve")
        elif tag == "text" and node.text:
            anchor = {"start": "ls", "middle": "ms", "end": "rs"}.get(node.attrib.get("text-anchor", "start"), "ls")
            size = int(node.attrib.get("font-size", 16))
            draw.text(
                (float(node.attrib["x"]), float(node.attrib["y"])),
                node.text,
                fill=node.attrib.get("fill", "#1f2933"),
                font=font(size, node.attrib.get("font-weight") == "bold"),
                anchor=anchor,
            )
    image.save(png_path, dpi=(180, 180), optimize=True)


def figure_sector_change_and_uncertainty() -> None:
    sectors = read_csv(OUTPUT_DIR / "sector_change_1990_2024.csv")
    uncertainty = [
        row
        for row in read_csv(OUTPUT_DIR / "sector_uncertainty_2024.csv")
        if row["sector"] != "Total"
    ]
    sectors.sort(key=lambda row: float(row["avoided_emissions_mtco2e"]), reverse=True)
    uncertainty.sort(key=lambda row: float(row["emissions_2024_mtco2e"]), reverse=True)

    width, height = 1500, 900
    elements: list[str] = []
    elements.append(text(65, 58, "Sector changes and uncertainty in territorial emissions", 28, weight="bold"))
    elements.append(text(65, 96, "a. Contribution to the UK reduction", 20, weight="bold"))
    elements.append(text(790, 96, "b. Published 2024 inventory uncertainty", 20, weight="bold"))

    left_label_x, left_x0, left_x1 = 255, 275, 700
    right_label_x, right_x0, right_x1 = 990, 1010, 1415
    plot_top, row_step = 145, 77
    max_reduction = 180.0
    max_emissions = 125.0

    for tick in range(0, 181, 30):
        x = left_x0 + (tick / max_reduction) * (left_x1 - left_x0)
        elements.append(line(x, 125, x, 755, LIGHT_GREY))
        elements.append(text(x, 785, str(tick), 14, anchor="middle", fill=GREY))
    elements.append(
        text((left_x0 + left_x1) / 2, 820, "Reduction from 1990 to 2024 (MtCO2e)", 16, anchor="middle")
    )

    for index, row in enumerate(sectors):
        y = plot_top + index * row_step
        value = float(row["avoided_emissions_mtco2e"])
        share = float(row["share_of_net_reduction"]) * 100
        bar_width = value / max_reduction * (left_x1 - left_x0)
        elements.append(text(left_label_x, y + 6, row["sector"], 15, anchor="end"))
        elements.append(
            f'<rect x="{left_x0}" y="{y - 17}" width="{bar_width:.1f}" height="34" rx="2" fill="{BLUE}"/>'
        )
        elements.append(text(left_x0 + bar_width + 9, y + 6, f"{value:.1f} ({share:.1f}%)", 14))

    for tick in range(0, 126, 25):
        x = right_x0 + (tick / max_emissions) * (right_x1 - right_x0)
        elements.append(line(x, 125, x, 755, LIGHT_GREY))
        elements.append(text(x, 785, str(tick), 14, anchor="middle", fill=GREY))
    elements.append(line(right_x0, 125, right_x0, 755, GREY, 1.4))
    elements.append(
        text((right_x0 + right_x1) / 2, 820, "Emissions and 95% range (MtCO2e)", 16, anchor="middle")
    )

    for index, row in enumerate(uncertainty):
        y = plot_top + index * row_step
        label = "LULUCF" if row["sector"].startswith("Land use") else row["sector"]
        central = float(row["emissions_2024_mtco2e"])
        lower = float(row["lower_95_mtco2e"])
        upper = float(row["upper_95_mtco2e"])
        scale = (right_x1 - right_x0) / max_emissions
        xc = right_x0 + central * scale
        xl = right_x0 + lower * scale
        xu = right_x0 + upper * scale
        elements.append(text(right_label_x, y + 6, label, 15, anchor="end"))
        elements.append(line(xl, y, xu, y, TEAL, 4))
        elements.append(line(xl, y - 8, xl, y + 8, TEAL, 2))
        elements.append(line(xu, y - 8, xu, y + 8, TEAL, 2))
        elements.append(f'<circle cx="{xc:.1f}" cy="{y:.1f}" r="6" fill="{NAVY}"/>')

    elements.append(
        text(
            65,
            868,
            "Panel a: UK only. Panel b: UK, Crown Dependencies and relevant Overseas Territories. LULUCF is a net balance.",
            14,
            fill=GREY,
        )
    )
    write_svg(FIGURE_DIR / "sector_change_and_uncertainty.svg", width, height, elements)


def compound_path(start: float, end: float, start_year: int, end_year: int) -> list[tuple[int, float]]:
    rate = math.pow(end / start, 1 / (end_year - start_year))
    return [(year, start * math.pow(rate, year - start_year)) for year in range(start_year, end_year + 1)]


def figure_ndc_pathways() -> None:
    observations = read_csv(OUTPUT_DIR / "ndc_observations_2021_2024.csv")
    ndc = load_ndc_inputs(SOURCE_PATH)
    pathways = calculate_pathways(ndc["base_year_mtco2e"], ndc["emissions_2024_mtco2e"])
    targets = {int(row["target_year"]): float(row["target_emissions_mtco2e"]) for row in pathways}

    observed = [(int(row["year"]), float(row["emissions_mtco2e"])) for row in observations]
    path_2030 = compound_path(observed[-1][1], targets[2030], 2024, 2030)
    path_2035 = compound_path(observed[-1][1], targets[2035], 2024, 2035)

    width, height = 1350, 820
    left, right, top, bottom = 105, 1280, 120, 690
    xmin, xmax, ymin, ymax = 2021, 2035, 120.0, 455.0

    def sx(year: float) -> float:
        return left + (year - xmin) / (xmax - xmin) * (right - left)

    def sy(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    elements: list[str] = []
    elements.append(text(65, 58, "Observed NDC-scope emissions and endpoint pathways", 28, weight="bold"))
    elements.append(
        f'<rect x="{sx(2024):.1f}" y="{top}" width="{right - sx(2024):.1f}" height="{bottom - top}" fill="{PALE}"/>'
    )
    elements.append(text(sx(2024) + 12, top + 25, "Diagnostic pathways", 14, fill=GREY))

    for tick in range(150, 451, 50):
        y = sy(tick)
        elements.append(line(left, y, right, y, LIGHT_GREY))
        elements.append(text(left - 14, y + 5, str(tick), 14, anchor="end", fill=GREY))
    for year in range(2021, 2036, 2):
        x = sx(year)
        elements.append(text(x, bottom + 30, str(year), 14, anchor="middle", fill=GREY))
    elements.append(line(left, bottom, right, bottom, GREY, 1.2))
    elements.append(line(left, top, left, bottom, GREY, 1.2))
    elements.append(text(left - 14, top - 14, "MtCO2e", 14, anchor="end", fill=GREY))
    elements.append(text((left + right) / 2, bottom + 52, "Year", 16, anchor="middle"))

    def path(points: list[tuple[int, float]], colour: str, dashed: bool = False) -> str:
        coords = " ".join(f"{sx(year):.1f},{sy(value):.1f}" for year, value in points)
        dash = ' stroke-dasharray="10 8"' if dashed else ""
        return (
            f'<polyline points="{coords}" fill="none" stroke="{colour}" stroke-width="4" '
            f'stroke-linejoin="round" stroke-linecap="round"{dash}/>'
        )

    elements.append(path(observed, NAVY))
    elements.append(path(path_2030, BLUE, dashed=True))
    elements.append(path(path_2035, ORANGE, dashed=True))

    for year, value in observed:
        elements.append(f'<circle cx="{sx(year):.1f}" cy="{sy(value):.1f}" r="6" fill="{NAVY}"/>')
    for year, colour in ((2030, BLUE), (2035, ORANGE)):
        elements.append(f'<circle cx="{sx(year):.1f}" cy="{sy(targets[year]):.1f}" r="7" fill="{colour}"/>')

    elements.append(
        text(
            sx(2030) + 10,
            sy(targets[2030]) - 20,
            f"2030 target: {targets[2030]:.1f} MtCO2e",
            15,
            fill=BLUE,
            weight="bold",
        )
    )
    elements.append(
        text(
            sx(2035) - 10,
            sy(targets[2035]) - 20,
            f"2035 target: {targets[2035]:.1f} MtCO2e",
            15,
            anchor="end",
            fill=ORANGE,
            weight="bold",
        )
    )

    legend_y = 92
    elements.append(line(710, legend_y, 755, legend_y, NAVY, 4))
    elements.append(text(765, legend_y + 5, "Final observations", 14))
    elements.append(line(905, legend_y, 950, legend_y, BLUE, 4, "10 8"))
    elements.append(text(960, legend_y + 5, "Path to 2030", 14))
    elements.append(line(1090, legend_y, 1135, legend_y, ORANGE, 4, "10 8"))
    elements.append(text(1145, legend_y + 5, "Path to 2035", 14))

    elements.append(
        text(
            65,
            772,
            "Observed scope: UK, Crown Dependencies and Gibraltar. Paths are arithmetic benchmarks from 2024, not forecasts.",
            14,
            fill=GREY,
        )
    )
    elements.append(
        text(65, 798, "The NDC headline targets exclude international aviation and shipping.", 14, fill=GREY)
    )
    write_svg(FIGURE_DIR / "ndc_pathways.svg", width, height, elements)


def figure_historical_pace() -> None:
    pace = [row for row in read_csv(OUTPUT_DIR / "ndc_historical_pace.csv") if row["annual_reduction_mtco2e"]]
    pathways = read_csv(OUTPUT_DIR / "ndc_pathway_diagnostics.csv")
    required = [float(row["constant_absolute_reduction_mtco2e_per_year"]) for row in pathways]

    width, height = 1500, 850
    left, right, top, bottom = 105, 1425, 125, 680
    xmin, xmax, ymin, ymax = 1991, 2024, -30.0, 60.0

    def sx(year: float) -> float:
        return left + (year - xmin) / (xmax - xmin) * (right - left)

    def sy(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    elements: list[str] = []
    elements.append(text(65, 58, "Historical emission reductions and required endpoint pace", 28, weight="bold"))
    for tick in range(-20, 61, 20):
        y = sy(tick)
        elements.append(line(left, y, right, y, LIGHT_GREY))
        elements.append(text(left - 14, y + 5, str(tick), 14, anchor="end", fill=GREY))
    elements.append(text(left - 14, top - 14, "MtCO2e/yr", 14, anchor="end", fill=GREY))
    elements.append(line(left, sy(0), right, sy(0), GREY, 1.5))

    target_low, target_high = min(required), max(required)
    target_y1, target_y2 = sy(target_high), sy(target_low)
    elements.append(
        f'<rect x="{left}" y="{target_y1:.1f}" width="{right - left}" height="{max(4, target_y2 - target_y1):.1f}" fill="#f4a261"/>'
    )
    bar_width = 25
    rolling_points: list[tuple[int, float]] = []
    for row in pace:
        year = int(row["year"])
        value = float(row["annual_reduction_mtco2e"])
        x = sx(year)
        y0, yv = sy(0), sy(value)
        fill = BLUE if value >= 0 else "#9aa4ad"
        elements.append(
            f'<rect x="{x - bar_width / 2:.1f}" y="{min(y0, yv):.1f}" width="{bar_width}" height="{abs(y0 - yv):.1f}" fill="{fill}"/>'
        )
        rolling = row["trailing_5y_mean_reduction_mtco2e_per_year"]
        if rolling:
            rolling_points.append((year, float(rolling)))

    coords = " ".join(f"{sx(year):.1f},{sy(value):.1f}" for year, value in rolling_points)
    elements.append(
        f'<polyline points="{coords}" fill="none" stroke="{NAVY}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    elements.append(
        f'<rect x="{right - 405}" y="{target_y1 - 42:.1f}" width="405" height="30" fill="white"/>'
    )
    elements.append(
        text(
            right - 8,
            target_y1 - 20,
            f"Required endpoint pace: {target_low:.1f}-{target_high:.1f} MtCO2e/yr",
            14,
            anchor="end",
            fill=ORANGE,
            weight="bold",
        )
    )

    for year in range(1992, 2025, 4):
        elements.append(text(sx(year), bottom + 30, str(year), 14, anchor="middle", fill=GREY))
    elements.append(line(left, bottom, right, bottom, GREY, 1.2))
    elements.append(text((left + right) / 2, bottom + 68, "Year", 16, anchor="middle"))

    elements.append(text(sx(2009), sy(55.9) - 12, "2009", 13, anchor="middle", fill=GREY))
    elements.append(text(sx(2020), sy(40.3) - 12, "2020", 13, anchor="middle", fill=GREY))

    legend_y = 96
    elements.append(f'<rect x="865" y="{legend_y - 10}" width="24" height="14" fill="{BLUE}"/>')
    elements.append(text(899, legend_y + 2, "Annual reduction", 14))
    elements.append(line(1050, legend_y - 3, 1090, legend_y - 3, NAVY, 4))
    elements.append(text(1100, legend_y + 2, "Trailing 5-year mean", 14))

    elements.append(
        text(
            65,
            780,
            "Positive bars indicate falling emissions. The 2009 and 2020 reductions coincide with major economic disruption and are not treated as sustained pathways.",
            14,
            fill=GREY,
        )
    )
    elements.append(
        text(
            65,
            808,
            "Series scope: UK, Crown Dependencies and Gibraltar, consistent with Paris Agreement reporting.",
            14,
            fill=GREY,
        )
    )
    write_svg(FIGURE_DIR / "historical_reduction_pace.svg", width, height, elements)


def main() -> None:
    prepare_tables()
    figure_sector_change_and_uncertainty()
    figure_ndc_pathways()
    figure_historical_pace()


if __name__ == "__main__":
    main()
