"""
Loading, validating and reshaping the multi-institution forecast table that
feeds the Growth Projections dashboard.

The table (data/projections/gdp_forecasts.csv) is tidy and vintage-keyed:
one row per (institution, vintage, target_year, indicator). Everything the
dashboard shows — the latest-forecast comparison, the revision history, the
consensus band — is derived here rather than in the app, so the reshaping is
testable without a Streamlit run context.
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
FORECASTS_CSV = DATA_DIR / "projections/gdp_forecasts.csv"

COLUMNS = [
    "institution", "institution_type", "vintage", "vintage_approx",
    "target_year", "kind", "indicator", "value", "low", "high", "unit",
    "source_url", "note",
]

# A projection table restates the base year's outturn alongside the forecast
# years. Those rows are worth keeping — each agency prints a slightly
# different base, which is itself informative — but they are history, not
# predictions, and scoring them against realized GDP would credit every
# forecaster with a perfect call.
KINDS = ("forecast", "actual")

# Indicator key -> (row label, unit, decimals). Order here is the row order
# of the detail table, and follows the shape of a published projection
# table: growth, demand components, trade volumes, trade values, external
# balances, tourism, prices, then the assumption and fiscal blocks.
#
# Labels must be unique on their own (asserted below) — two indicators can
# otherwise collide when a frame is keyed on the label, which is why the two
# current-account rows carry their unit in the label, exactly as a published
# table prints them.
INDICATORS = {
    "gdp_growth":            ("GDP", "%", 1),
    "domestic_demand":       ("Domestic demand", "%", 1),
    "private_consumption":   ("PCE — private consumption", "%", 1),
    "public_consumption":    ("GCE — government consumption", "%", 1),
    "gfcf":                  ("GFCF — total investment", "%", 1),
    "private_investment":    ("GFCF — private", "%", 1),
    "public_investment":     ("GFCF — public", "%", 1),
    "exports_volume":        ("Exports of goods and services", "%", 1),
    "exports_goods_volume":  ("Exports of goods", "%", 1),
    "exports_services":      ("Exports of services", "%", 1),
    "imports_volume":        ("Imports of goods and services", "%", 1),
    "imports_goods_volume":  ("Imports of goods", "%", 1),
    "imports_services":      ("Imports of services", "%", 1),
    "exports_value":         ("Exports of goods, USD BOP", "%", 1),
    "imports_value":         ("Imports of goods, USD BOP", "%", 1),
    "trade_balance_usdbn":   ("Trade balance, USD billion", "USD bn", 1),
    "current_account_usdbn": ("Current account balance, USD billion", "USD bn", 1),
    "current_account_gdp":   ("Current account balance, %GDP", "% of GDP", 1),
    "tourist_arrivals":      ("Number of foreign tourists", "million persons", 1),
    "headline_inflation":    ("Headline CPI", "%", 1),
    "core_inflation":        ("Core CPI", "%", 1),
    "gdp_deflator":          ("GDP deflator", "%", 1),
    "policy_rate":           ("Policy rate (end of period)", "%", 2),
    "usd_thb":               ("USD/THB", "baht per USD", 2),
    "oil_dubai":             ("Dubai oil, USD/bbl", "USD/bbl", 1),
    "fiscal_balance":        ("Fiscal balance", "% of GDP", 1),
    "public_debt_gdp":       ("Public debt to GDP", "% of GDP", 1),
    "tourism_receipts":      ("Tourist revenue (THB trillion)", "trillion baht", 2),
    "tourism_receipts_per_trip": ("Tourist revenue per person/trip", "baht", 0),
}
assert len({v[0] for v in INDICATORS.values()}) == len(INDICATORS), \
    "INDICATORS labels must be unique — a wide table keyed on the label collides otherwise"

# Rows drawn as main aggregates (bold, shaded band); everything else is an
# indented sub-component, matching how the monitor's GDP detail tables treat
# indent-0 rows.
MAIN_ROWS = frozenset({
    "gdp_growth", "private_consumption", "public_consumption", "gfcf",
    "exports_volume", "imports_volume", "exports_value", "imports_value",
    "current_account_usdbn", "tourist_arrivals", "headline_inflation",
    "fiscal_balance", "tourism_receipts",
})

# Indicator -> column in data/reference/gdp_expenditure_share.csv, so the
# "share of GDP" column is computed from the national accounts rather than
# hardcoded and left to drift. See data/reference/README.md for provenance.
SHARE_COLUMNS = {
    "private_consumption": "pce",
    "public_consumption": "gce",
    "gfcf": "gfcf_total",
    "private_investment": "gfcf_private",
    "public_investment": "gfcf_public",
    "exports_volume": "exports_gs",
    "exports_goods_volume": "exports_goods",
    "exports_services": "exports_services",
    "imports_volume": "imports_gs",
    "imports_goods_volume": "imports_goods",
    "imports_services": "imports_services",
}

EXPECTED_INSTITUTIONS = [
    ("NESDC", "official"),
    ("FPO", "official"),
    ("BOT", "official"),
    ("World Bank TEM", "international"),
    ("World Bank MPO", "international"),
    ("SCB EIC", "bank"),
    ("KKP Research", "bank"),
    ("KResearch", "bank"),
    ("Krungsri Research", "bank"),
    ("Citi", "bank"),
]

INSTITUTION_TYPES = {
    "official":      "Thai official (NESDC / BOT / FPO)",
    "international": "International organisation (IMF / WB / ADB / OECD)",
    "bank":          "Bank & private research",
    "other":         "Other",
}

_NUMERIC = ("value", "low", "high")


def _empty() -> pd.DataFrame:
    df = pd.DataFrame(columns=COLUMNS)
    df["vintage"] = pd.to_datetime(df["vintage"])
    return df


def load_forecasts(path: Path | str | None = None) -> pd.DataFrame:
    """Read the forecast table, normalized: `vintage` as datetime,
    `target_year` as int, value/low/high as float. Returns an empty frame
    with the right columns if the file is missing or has no rows, so callers
    can branch on `.empty` instead of guarding for a KeyError."""
    path = Path(path) if path is not None else FORECASTS_CSV
    if not path.exists():
        return _empty()
    df = pd.read_csv(path)
    if df.empty:
        return _empty()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df["vintage"] = pd.to_datetime(df["vintage"], errors="coerce")
    df["vintage_approx"] = (
        df["vintage_approx"].astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])
    )
    df["target_year"] = pd.to_numeric(df["target_year"], errors="coerce").astype("Int64")
    df["kind"] = df["kind"].fillna("forecast").astype(str).str.strip().str.lower()
    for col in _NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["vintage", "target_year", "indicator", "institution"])
    return df[COLUMNS].sort_values(["target_year", "indicator", "institution", "vintage"])


def validate(df: pd.DataFrame) -> list[str]:
    """Structural problems with the forecast table, as human-readable lines.
    Empty list means clean. Used by scripts/check_projections.py in CI and
    surfaced on the dashboard's own Data & Sources tab, so a bad hand-edit
    is visible in both places rather than silently drawn as a gap."""
    problems = []
    if df.empty:
        return problems

    unknown = sorted(set(df["indicator"].dropna()) - set(INDICATORS))
    for key in unknown:
        problems.append(
            f'unknown indicator "{key}" — add it to INDICATORS in '
            "projections_io.py or fix the spelling"
        )

    bad_kind = sorted(set(df["kind"].dropna()) - set(KINDS))
    for key in bad_kind:
        problems.append(f'unknown kind "{key}" — expected one of {", ".join(KINDS)}')

    bad_type = sorted(set(df["institution_type"].dropna()) - set(INSTITUTION_TYPES))
    for key in bad_type:
        problems.append(
            f'unknown institution_type "{key}" — expected one of '
            f"{', '.join(INSTITUTION_TYPES)}"
        )

    key_cols = ["institution", "vintage", "target_year", "indicator"]
    dupes = df[df.duplicated(key_cols, keep=False)]
    for _, row in dupes.drop_duplicates(key_cols).iterrows():
        problems.append(
            f"duplicate rows for {row['institution']} / "
            f"{row['vintage']:%Y-%m-%d} / {row['target_year']} / {row['indicator']} — "
            "one forecast per institution per vintage per indicator"
        )

    banded = df.dropna(subset=["low", "high"])
    inverted = banded[banded["low"] > banded["high"]]
    for _, row in inverted.iterrows():
        problems.append(
            f"{row['institution']} {row['target_year']} {row['indicator']}: "
            f"low ({row['low']}) is above high ({row['high']})"
        )

    # Only bracket-check well-ordered bands: an inverted one is already
    # reported above, and "outside its published range [2.0, 1.5]" reads as
    # nonsense when the range itself is the problem.
    ordered = banded[banded["low"] <= banded["high"]]
    outside = ordered[(ordered["value"] < ordered["low"]) | (ordered["value"] > ordered["high"])]
    for _, row in outside.iterrows():
        problems.append(
            f"{row['institution']} {row['target_year']} {row['indicator']}: "
            f"value {row['value']} is outside its published range "
            f"[{row['low']}, {row['high']}]"
        )
    return problems


def forecasts_only(df: pd.DataFrame) -> pd.DataFrame:
    """Drop restated-outturn rows. Every view that treats a row as a
    prediction — comparison, revisions, consensus, outturn scoring — must go
    through this first."""
    return df[df["kind"] == "forecast"] if not df.empty else df


def latest_vintage(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (institution, target_year, indicator) — the most recent
    vintage. This is the 'where does everyone stand today' view."""
    if df.empty:
        return df
    idx = df.groupby(["institution", "target_year", "indicator"])["vintage"].idxmax()
    return df.loc[idx].sort_values(["target_year", "indicator", "value"])


def revision_history(df: pd.DataFrame, indicator: str, target_year: int) -> pd.DataFrame:
    """Every vintage of every institution's forecast for one indicator/year,
    sorted for plotting as one line per institution against vintage date."""
    if df.empty:
        return df
    out = forecasts_only(df)
    out = out[(out["indicator"] == indicator) & (out["target_year"] == target_year)]
    return out.sort_values(["institution", "vintage"])


def consensus(df: pd.DataFrame, indicator: str, target_year: int) -> pd.DataFrame:
    """Cross-institution mean/median/min/max by vintage month, using each
    institution's forecast as of that month (its latest vintage up to and
    including that month) so an institution that has not revised recently
    still counts toward the consensus instead of dropping out of it."""
    hist = revision_history(df, indicator, target_year)
    if hist.empty:
        return pd.DataFrame(columns=["month", "mean", "median", "min", "max", "n"])
    hist = hist.assign(month=hist["vintage"].dt.to_period("M").dt.to_timestamp())
    months = pd.date_range(hist["month"].min(), hist["month"].max(), freq="MS")
    rows = []
    for month in months:
        upto = hist[hist["month"] <= month]
        if upto.empty:
            continue
        current = upto.sort_values("vintage").groupby("institution").tail(1)
        vals = current["value"].dropna()
        if vals.empty:
            continue
        rows.append({
            "month": month, "mean": vals.mean(), "median": vals.median(),
            "min": vals.min(), "max": vals.max(), "n": int(vals.size),
        })
    return pd.DataFrame(rows)


def indicator_label(key: str) -> str:
    return INDICATORS.get(key, (key, ""))[0]


def indicator_unit(key: str) -> str:
    return INDICATORS.get(key, (key, ""))[1]


def indicator_decimals(key: str) -> int:
    return INDICATORS.get(key, (key, "", 1))[2]


def gdp_shares() -> dict:
    """Latest-year expenditure shares of GDP, keyed by indicator, read from
    the national accounts snapshot in data/reference/. Empty dict if that
    file is missing — the share column just goes blank."""
    path = DATA_DIR / "reference/gdp_expenditure_share.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if df.empty:
        return {}
    row = df.sort_values("year").iloc[-1]
    out = {"gdp_growth": 100.0}
    for key, col in SHARE_COLUMNS.items():
        if col in row.index and pd.notna(row[col]):
            out[key] = float(row[col])
    return out


def available_indicators(df: pd.DataFrame) -> list[str]:
    """Indicator keys actually present in the data, in INDICATORS order,
    with any unrecognised keys appended so nothing in the file is invisible
    on the dashboard just because it is not catalogued yet."""
    if df.empty:
        return []
    present = set(df["indicator"].dropna())
    known = [k for k in INDICATORS if k in present]
    return known + sorted(present - set(INDICATORS))
