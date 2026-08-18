# Growth projections — multi-institution forecast table

`gdp_forecasts.csv` is a **hand-maintained** tidy table: one row per
(institution, vintage, target year, indicator). It is the only data source
for the Growth Projections dashboard (`app.py`).

Nothing fetches it automatically. Published forecasts arrive as PDFs and
press conferences on no fixed machine-readable schedule, so this file is
appended to by hand — or by a future parser — as each institution publishes.

## Running the dashboard

```
streamlit run app.py
```

## Layout config

Three registries in `projections_io.py` control how the detail table
is drawn, and are the place to change it:

- `INDICATORS` — row order, row label, unit and decimals. Labels must be
  unique (asserted on import): a wide table keyed on the label collides
  otherwise, which is why the two current-account rows carry their unit in
  the label the way a published table prints them.
- `MAIN_ROWS` — which rows are drawn as bold, shaded aggregates; everything
  else is an indented sub-component.
- `SHARE_COLUMNS` — maps an indicator to its column in
  `data/reference/gdp_expenditure_share.csv`, so the "Share of GDP" column is
  computed from the monitor's own national accounts rather than hardcoded
  and left to drift.

Rows with no data anywhere, and institutions in `EXPECTED_INSTITUTIONS` with
no rows, are still drawn — as empty slots waiting to be filled, not omissions.

## Rules

- **Never edit a past vintage to reflect a newer forecast.** Append a new row
  with the new `vintage`. The revision charts are the whole point of the
  file, and they are computed from the vintage history.
- One row per (institution, vintage, target_year, indicator). Duplicates are
  flagged by `scripts/check_projections.py`.
- Percentages go in as numbers, not strings: `1.8`, not `1.8%` or `"1.8"`.
- `value` should be a number the source actually prints. The one exception in
  the file today is NESDC's GDP deflator, where NESDC publishes a range but no
  central value — that row carries the computed midpoint and says so in `note`.
- Where two indicators share a label and differ only by unit (the current
  account, published both in USD bn and as a share of GDP), they are separate
  keys: `current_account_usdbn` and `current_account_gdp`.

## Validating

```
python scripts/check_projections.py
```

Exits non-zero on unknown indicators, bad dates, duplicate keys, or a `low`/
`high` band that does not bracket `value`.
