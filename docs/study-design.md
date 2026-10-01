# Study design

## Scientific question

Which UK source sectors drove the change in territorial greenhouse gas emissions from 1990 to 2024, and what annual reduction from the final 2024 NDC-scope estimate would be consistent with the 2030 and 2035 NDC thresholds?

## Evidence classes

### Observations

Final DESNZ estimates for 1990-2024. Table 1.2 supplies UK-only source-sector totals. Table 2.2 supplies the composite NDC base year, the 2021-2024 NDC-scope observations and the 2030 target.

### Targets

- 2030: at least 68% below the composite base year.
- 2035: at least 81% below the composite base year.

The composite base year is 1990 for carbon dioxide, methane and nitrous oxide, and 1995 for fluorinated gases. The analysis uses the published composite total rather than reconstructing it.

### Diagnostic pathways

Two simple pathways begin at the final 2024 NDC-scope observation:

1. Constant absolute reduction, with the same MtCO2e reduction each year.
2. Constant percentage reduction, with the same proportional reduction each year.

These pathways measure the scale and pace of change implied by the endpoints. They do not represent DESNZ projections, a policy scenario or a prediction.

## Calculations

For sector `s`:

```text
sector_change_s = E_s,2024 - E_s,1990
avoided_emissions_s = E_s,1990 - E_s,2024
share_of_net_reduction_s = avoided_emissions_s / (E_total,1990 - E_total,2024)
```

The contribution shares can be negative where a sector's emissions increased. LULUCF is a net source or sink and is retained with its published sign.

For target year `T`, reduction fraction `r`, base-year emissions `E_base`, current emissions `E_2024` and `n = T - 2024`:

```text
E_target = E_base * (1 - r)
remaining_gap = E_2024 - E_target
constant_absolute_reduction = remaining_gap / n
constant_percentage_reduction = 1 - (E_target / E_2024) ** (1 / n)
```

## Quality checks

- Confirm the source checksum before processing.
- Confirm Table 1.2 is explicitly UK-only.
- Reconcile the sum of the eight published sector totals with the grand total for 1990 and 2024.
- Read the 2030 base year, 2024 observation and target from Table 2.2.
- Recalculate the published 2030 target from the base year and 68% reduction.
- Keep the UK-only sector series separate from the wider NDC-scope series.

## Limitations

- Territorial emissions do not measure the UK's consumption-based carbon footprint.
- The NDC scope differs from the UK-only source-sector table.
- Inventory estimates are revised when methods and input data improve.
- Sector contributions are an accounting decomposition, not a causal attribution.
- Straight-line and compound pathways do not model technology, policy, cost, behaviour or carbon-budget accounting.
- DESNZ publishes sector uncertainty for a wider geographical scope than the UK-only sector table. The intervals are therefore reported separately and are not propagated into the UK-only contribution estimates or NDC pathways.

