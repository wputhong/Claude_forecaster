# Thailand Growth Projections

A Streamlit dashboard comparing published economic projections for Thailand
across forecasting institutions — what each one expects, how each has revised,
and where the consensus sits.

```
pip install -r requirements.txt
streamlit run app.py
```

## Deploying to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app** → **Deploy a public app from GitHub** (this repo is private,
   so authorize Streamlit for private repos when prompted).
3. Fill in:
   - Repository: `wputhong/Claude_forecaster`
   - Branch: `main`
   - Main file path: `app.py`
4. Under **Advanced settings**, set Python version to **3.11** — the version
   the pinned dependencies were tested against.
5. Deploy. The URL is chosen at deploy time; you can set a custom subdomain
   in the same dialog.

Dependencies are pinned in `requirements.txt` on purpose. Streamlit's layout
API is actively churning, so an unpinned deploy can break on a release that
lands between pushes. When bumping, run the app locally first.

Nothing here needs secrets — no API keys, no database. Every input is a CSV
committed to the repo, so a deploy is just install-and-run.

## Views

| View | What it shows |
| --- | --- |
| **Detail Comparison** | The full projection detail as one wide table — indicator rows, a share-of-GDP column, the base-year outturn, then every agency side by side for the current and next year. |
| **Forecast Comparison** | One indicator, one year: every agency's latest number as a dot plot with published ranges, plus mean/median/spread. |
| **Forecast Revisions** | How each agency's view of a single year has moved across publication rounds, and the change between its two most recent. |
| **Consensus & Dispersion** | Cross-agency mean and median with the full min–max band, month by month. |
| **Forecast vs Outturn** | Forecasts scored against realized annual growth, with a per-agency error table. |
| **Data & Sources** | The whole table as it sits on disk, live validator output, and CSV download. |

## The data

Everything is driven by one hand-maintained file: `data/projections/gdp_forecasts.csv`,
a tidy table with one row per (institution, vintage, target year, indicator).
See [`data/projections/README.md`](data/projections/README.md) for the schema
and the rules that keep it useful.

**Nothing fetches it.** Published forecasts arrive as PDFs and press
conferences on no machine-readable schedule, so rounds are appended by hand as
each institution publishes. Because a typo would land straight on the
dashboard, `scripts/check_projections.py` guards the silent failure modes —
unknown indicator keys, duplicate vintage keys, bands that do not bracket
their own point forecast — and runs in CI.

The one rule worth repeating: **append a new vintage, never edit an old one.**
Revision history is the thing this dashboard exists to show, and overwriting a
past round destroys it irrecoverably.

### Currently loaded

Six forecasters, transcribed from their own projection tables:

| Agency | Round | Covers |
| --- | --- | --- |
| NESDC | 17 Aug 2026, plus the 18 May 2026 round it restates | 2026 |
| BOT | Monetary Policy Report Q2/2026, plus the Q1/2026 figures in parentheses | 2026, 2027 |
| FPO | July 2026 round, plus the April 2026 round it restates | 2026 |
| SCB EIC | Monthly insight, 23 Jul 2026 | 2026, 2027 |
| KKP Research | Jul 2026 update, both its Previous and Current columns | 2026, 2027 |
| Krungsri Research | Jul 2026 monthly bulletin | 2026 |

World Bank TEM, World Bank MPO, KResearch and Citi are declared in
`EXPECTED_INSTITUTIONS` but hold no rows yet. They render as visible gaps
rather than disappearing from the comparison — add their rows to fill them in.

### Two honesties baked into the schema

- `kind` separates a forecast from a base-year row restating an agency's own
  outturn. Projection tables print the base year next to the forecast years,
  and each agency's base differs slightly, so the rows are worth keeping — but
  scoring them against realized GDP would credit every forecaster with a
  perfect call.
- `vintage_approx` marks rounds whose source names the round ("Q2/2026",
  "July round") but not an exact date. Those values render greyed. Round
  *ordering* is correct; the exact day is not.

## Layout

Three registries in `projections_io.py` drive the detail table, so the table
changes by editing config rather than the renderer: `INDICATORS` (row order,
label, unit, decimals), `MAIN_ROWS` (bold shaded aggregates vs indented
sub-components), and `SHARE_COLUMNS` (which national-accounts column supplies
each share).

## Reference data

`data/reference/` holds two small snapshots from the Thailand economic monitor
repository — quarterly GDP for outturn scoring, and expenditure shares for the
share column. They are snapshots, not a feed; see
[`data/reference/README.md`](data/reference/README.md) for how to refresh them.
