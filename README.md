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

Nothing here needs secrets — no API keys, no database. Every input is a CSV
committed to the repo, so a deploy is just install-and-run.

`requirements.txt` uses version *ranges*, not exact pins. The floors are what
the app was verified against; the ceilings stop a major release breaking it.
Exact pins are tempting but backfire here: streamlit depends on pyarrow, a
heavy C++ package, and over-constraining the resolver is how a deploy ends up
building it from source rather than taking a prebuilt wheel.

### If the app is slow to load or never appears

The app itself is not the bottleneck — it reads a 305-row CSV and renders in
well under a second once running. Slowness is almost always the environment:

1. **It is asleep.** Community Cloud suspends apps after inactivity; the next
   visit takes ~30s to wake. This is the most common cause and needs no fix.
2. **It is still building.** A first deploy installs pandas, pyarrow and
   streamlit. Open **Manage app → logs** (bottom right of the app page) and
   watch. If a log line shows pyarrow or pandas *building a wheel* rather than
   downloading one, the Python version has no matching wheel — set Python to
   **3.11** in the app's settings and reboot.
3. **It ran out of memory.** The free tier caps at about 1 GB. A source build
   of pyarrow will exceed it; the app itself will not come close.
4. **Streamlit lost access to the repo.** This repo is private, so if the
   GitHub authorization was revoked the app cannot pull and will hang. Check
   under Streamlit's GitHub app permissions.

The logs under **Manage app** name the actual cause; the four above cover
essentially every case.

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
