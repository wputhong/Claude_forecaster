# Reference data — snapshots, not a live feed

Two small CSVs copied from the Thailand economic monitor repository. Neither
is produced here, and nothing in this repo refreshes them.

| File | Used for | Shape |
| --- | --- | --- |
| `gdp.csv` | Realized annual GDP growth on the **Forecast vs Outturn** view, summed from the quarterly series. Only complete four-quarter years are scored. | `period,value` — quarterly real GDP, CVM, million baht |
| `gdp_expenditure_share.csv` | The **Share of GDP** column on the detail table, taken from the latest year available. | one row per year, one column per expenditure component |

## Refreshing

Copy the newer file over the old one after a NESDC quarterly GDP release:

```
cp <monitor-repo>/data/real/gdp.csv                   data/reference/gdp.csv
cp <monitor-repo>/data/real/gdp_expenditure_share.csv data/reference/gdp_expenditure_share.csv
```

Both are read defensively — if a file is missing or empty the share column
goes blank and the outturn view says so, rather than the app failing.

Staleness is visible rather than silent: an out-of-date `gdp.csv` simply
scores one fewer completed year, and an out-of-date share file shows shares
from an earlier year. Neither corrupts a forecast figure, which is why
snapshotting is acceptable here instead of wiring up the monitor's full
fetch pipeline.
