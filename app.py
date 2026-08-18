"""
Thailand Growth Projections Dashboard

Charts what forecasters expect the Thai economy to do: every institution's
published projection, every vintage of it, and how the consensus has moved.

Run:  streamlit run app.py
Data: data/projections/gdp_forecasts.csv (see that folder's README)
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import projections_io as pio
import projections_table_html
from chart_theme import (
    PALETTE, TOTAL_COLOR, apply_time_xaxis, axis, font, legend_bottom,
)

st.set_page_config(
    page_title="Thailand Growth Projections",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Institution groups keep their own colors across every chart, so NESDC is
# the same navy on the comparison chart and the revision chart.
TYPE_COLORS = {
    "official":      PALETTE[0],
    "international": PALETTE[5],
    "bank":          PALETTE[7],
    "other":         PALETTE[2],
}


@st.cache_data(ttl=600)
def _load() -> pd.DataFrame:
    return pio.load_forecasts()


def _institution_colors(institutions: list[str], df: pd.DataFrame) -> dict:
    """One stable color per institution: its group color for the first
    institution in each group, then distinct palette entries after that, so
    a legend with four banks in it is still readable."""
    types = df.drop_duplicates("institution").set_index("institution")["institution_type"]
    used, seen_group, out = set(), set(), {}
    spare = [c for c in PALETTE[1:] if c not in TYPE_COLORS.values()]
    for inst in institutions:
        group = types.get(inst, "other")
        base = TYPE_COLORS.get(group, PALETTE[2])
        if group not in seen_group:
            seen_group.add(group)
            out[inst] = base
            used.add(base)
            continue
        for color in spare:
            if color not in used:
                out[inst] = color
                used.add(color)
                break
        else:
            out[inst] = base
    return out


def _no_data_notice():
    st.info(
        "**No forecasts loaded yet.** This dashboard reads "
        "`data/projections/gdp_forecasts.csv`, which currently has headers "
        "but no rows.\n\n"
        "Add one row per institution per publication round — see "
        "`data/projections/README.md` for the column meanings and the "
        "append-don't-overwrite rule that makes the revision charts work."
    )
    st.code(
        "institution,institution_type,vintage,vintage_approx,target_year,kind,"
        "indicator,value,low,high,unit,source_url,note\n"
        "NESDC,official,2026-08-17,false,2026,forecast,gdp_growth,2.2,2.0,2.5,%,"
        "https://www.nesdc.go.th/,illustrative row only",
        language="text",
    )
    st.caption(
        "The row above is a format example, not a real published forecast — "
        "no projection figures are shipped in this repo."
    )


def _pick_year_indicator(df: pd.DataFrame, key: str):
    years = sorted(int(y) for y in df["target_year"].dropna().unique())
    indicators = pio.available_indicators(df)
    c1, c2 = st.columns(2)
    with c1:
        year = st.selectbox(
            "Target year", years, index=len(years) - 1, key=f"{key}_year",
        )
    with c2:
        indicator = st.selectbox(
            "Indicator", indicators, index=0,
            format_func=pio.indicator_label, key=f"{key}_indicator",
        )
    return year, indicator


def _download(df: pd.DataFrame, filename: str, key: str):
    st.download_button(
        "⬇ Download CSV", data=df.to_csv(index=False).encode(),
        file_name=filename, mime="text/csv", key=key,
    )


# ── Comparison ────────────────────────────────────────────────────────────────
def comparison_section(df: pd.DataFrame):
    st.title("Forecast Comparison")
    st.caption(
        "Where every forecaster stands right now — each institution's most "
        "recent published projection for the selected year, with its "
        "published range where it publishes one."
    )
    fdf = pio.forecasts_only(df)
    year, indicator = _pick_year_indicator(fdf, "cmp")
    latest = pio.latest_vintage(fdf)
    sel = latest[(latest["target_year"] == year) & (latest["indicator"] == indicator)]
    sel = sel.sort_values("value")
    if sel.empty:
        st.warning(f"No {pio.indicator_label(indicator)} forecasts for {year} yet.")
        return

    unit = sel["unit"].dropna().iloc[0] if sel["unit"].notna().any() else pio.indicator_unit(indicator)
    colors = _institution_colors(list(sel["institution"]), df)

    fig = go.Figure()
    # Published ranges as real traces rather than layout shapes: a shape does
    # not participate in autorange, so a band wider than the spread of point
    # forecasts would be clipped at the axis edge.
    banded = sel.dropna(subset=["low", "high"])
    for _, row in banded.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["low"], row["high"]], y=[row["institution"], row["institution"]],
            mode="lines",
            line=dict(color=colors.get(row["institution"], TOTAL_COLOR), width=6),
            opacity=0.3, showlegend=False,
            hovertemplate=(
                f"{row['institution']} range: {row['low']:,.2f}–{row['high']:,.2f} "
                + unit + "<extra></extra>"
            ),
        ))
    fig.add_trace(go.Scatter(
        x=sel["value"], y=sel["institution"], mode="markers",
        marker=dict(size=12, color=[colors.get(i, TOTAL_COLOR) for i in sel["institution"]]),
        name="Point forecast",
        customdata=sel[["vintage", "low", "high"]].assign(
            vintage=sel["vintage"].dt.strftime("%d %b %Y")).values,
        hovertemplate=(
            "%{y}: %{x:,.2f} " + unit
            + "<br>as of %{customdata[0]}<extra></extra>"
        ),
        showlegend=False,
    ))
    mean = sel["value"].mean()
    fig.add_vline(
        x=mean, line=dict(color="#c3c2b7", width=1, dash="dash"),
        annotation_text=f"mean {mean:,.2f}", annotation_position="top",
        annotation_font=font(size=11, color="#7a7a70"),
    )
    fig.update_layout(
        title=dict(text=f"{pio.indicator_label(indicator)} — {year} forecasts", font_size=14),
        height=max(320, 60 + 34 * len(sel)),
        margin=dict(l=10, r=10, t=44, b=10), font=font(),
        xaxis=axis(title=unit, zeroline=True), yaxis=axis(),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig, width="stretch", key="cmp_chart")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Forecasters", f"{len(sel)}")
    c2.metric(f"Mean ({unit})", f"{mean:,.2f}")
    c3.metric(f"Median ({unit})", f"{sel['value'].median():,.2f}")
    c4.metric(f"Spread ({unit})", f"{sel['value'].max() - sel['value'].min():,.2f}")

    st.markdown("---")
    st.subheader("Across indicators")
    st.caption("Latest vintage per institution, all indicators, for the selected year.")
    year_rows = latest[latest["target_year"] == year]
    wide = year_rows.pivot_table(
        index="institution", columns="indicator", values="value", aggfunc="last",
    )
    order = [i for i in pio.available_indicators(df) if i in wide.columns]
    wide = wide[order].rename(columns=pio.indicator_label)
    st.dataframe(wide.style.format("{:,.2f}"), width="stretch")
    _download(wide.reset_index(), f"thailand_forecasts_{year}.csv", "dl_cmp")


# ── Revisions ─────────────────────────────────────────────────────────────────
def revisions_section(df: pd.DataFrame):
    st.title("Forecast Revisions")
    st.caption(
        "How each institution's view of a single year has moved over "
        "successive publication rounds — the x-axis is the *vintage* "
        "(publication date), not the forecast horizon."
    )
    year, indicator = _pick_year_indicator(pio.forecasts_only(df), "rev")
    hist = pio.revision_history(df, indicator, year)
    if hist.empty:
        st.warning(f"No {pio.indicator_label(indicator)} forecasts for {year} yet.")
        return
    if hist["vintage"].nunique() < 2:
        st.info(
            "Only one vintage on file so far — revisions appear once a second "
            "publication round is added for this year."
        )

    unit = hist["unit"].dropna().iloc[0] if hist["unit"].notna().any() else pio.indicator_unit(indicator)
    institutions = sorted(hist["institution"].unique())
    colors = _institution_colors(institutions, df)

    fig = go.Figure()
    for inst in institutions:
        sub = hist[hist["institution"] == inst]
        fig.add_trace(go.Scatter(
            x=sub["vintage"], y=sub["value"], mode="lines+markers",
            name=inst, line=dict(color=colors.get(inst, TOTAL_COLOR), width=2),
            marker=dict(size=6),
            hovertemplate="%{y:,.2f} " + unit + "<extra>" + inst + "</extra>",
        ))
    fig.update_layout(
        title=dict(text=f"{pio.indicator_label(indicator)} for {year} — by vintage", font_size=14),
        height=440, margin=dict(l=10, r=10, t=44, b=10), font=font(),
        xaxis=axis(), yaxis=axis(title=unit, zeroline=True),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified", legend=legend_bottom(),
    )
    apply_time_xaxis(fig)
    st.plotly_chart(fig, width="stretch", key="rev_chart")

    st.subheader("Latest revision")
    st.caption("Change between each institution's two most recent vintages.")
    rows = []
    for inst in institutions:
        sub = hist[hist["institution"] == inst].sort_values("vintage")
        current = sub.iloc[-1]
        previous = sub.iloc[-2] if len(sub) >= 2 else None
        rows.append({
            "Institution": inst,
            "Latest": current["value"],
            "As of": current["vintage"].strftime("%d %b %Y"),
            "Previous": previous["value"] if previous is not None else None,
            "Prior vintage": previous["vintage"].strftime("%d %b %Y") if previous is not None else "—",
            "Change": (current["value"] - previous["value"]) if previous is not None else None,
        })
    table = pd.DataFrame(rows).sort_values("Latest", ascending=False)
    st.dataframe(
        table.style.format({"Latest": "{:,.2f}", "Previous": "{:,.2f}", "Change": "{:+,.2f}"},
                           na_rep="—")
        .map(lambda v: "color: #C00000" if isinstance(v, float) and v < 0
             else ("color: #548235" if isinstance(v, float) and v > 0 else ""),
             subset=["Change"]),
        width="stretch", hide_index=True,
    )
    _download(table, f"forecast_revisions_{indicator}_{year}.csv", "dl_rev")


# ── Consensus ─────────────────────────────────────────────────────────────────
def consensus_section(df: pd.DataFrame):
    st.title("Consensus & Dispersion")
    st.caption(
        "The cross-forecaster mean and the full min–max range, month by "
        "month. An institution that has not revised recently still counts — "
        "its most recent forecast carries forward — so the consensus does "
        "not jump around purely because of publication timing."
    )
    year, indicator = _pick_year_indicator(pio.forecasts_only(df), "con")
    cons = pio.consensus(df, indicator, year)
    if cons.empty:
        st.warning(f"No {pio.indicator_label(indicator)} forecasts for {year} yet.")
        return
    unit = pio.indicator_unit(indicator)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cons["month"], y=cons["max"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=cons["month"], y=cons["min"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(147,205,221,0.35)",
        name="Min–max range", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=cons["month"], y=cons["mean"], mode="lines+markers",
        line=dict(color=TOTAL_COLOR, width=2.5), marker=dict(size=5), name="Mean",
        customdata=cons[["n", "min", "max"]].values,
        hovertemplate=(
            "mean %{y:,.2f} " + unit
            + "<br>range %{customdata[1]:,.2f}–%{customdata[2]:,.2f}"
            + "<br>%{customdata[0]} forecasters<extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=cons["month"], y=cons["median"], mode="lines",
        line=dict(color=PALETTE[4], width=1.5, dash="dot"), name="Median",
        hovertemplate="median %{y:,.2f} " + unit + "<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Consensus {pio.indicator_label(indicator)} for {year}", font_size=14),
        height=440, margin=dict(l=10, r=10, t=44, b=10), font=font(),
        xaxis=axis(), yaxis=axis(title=unit, zeroline=True),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified", legend=legend_bottom(),
    )
    apply_time_xaxis(fig)
    st.plotly_chart(fig, width="stretch", key="con_chart")

    latest = cons.iloc[-1]
    first = cons.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Consensus ({unit})", f"{latest['mean']:,.2f}",
              delta=f"{latest['mean'] - first['mean']:+,.2f} since {first['month']:%b %Y}")
    c2.metric(f"Dispersion ({unit})", f"{latest['max'] - latest['min']:,.2f}")
    c3.metric("Forecasters", f"{int(latest['n'])}")
    _download(cons, f"consensus_{indicator}_{year}.csv", "dl_con")


# ── Forecast vs outturn ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _annual_gdp_growth() -> pd.DataFrame:
    """Realized annual real GDP growth, summed from the quarterly CVM series
    snapshot in data/reference/gdp.csv. Only complete years — a part-year sum
    would understate growth and read as a forecast miss."""
    path = pio.DATA_DIR / "reference/gdp.csv"
    if not path.exists():
        return pd.DataFrame(columns=["year", "growth"])
    gdp = pd.read_csv(path)
    gdp["period"] = pd.to_datetime(gdp["period"], errors="coerce")
    gdp = gdp.dropna(subset=["period"])
    if gdp.empty:
        return pd.DataFrame(columns=["year", "growth"])
    annual = gdp.assign(year=gdp["period"].dt.year).groupby("year").agg(
        total=("value", "sum"), quarters=("value", "size"))
    annual = annual[annual["quarters"] == 4]
    annual["growth"] = annual["total"].pct_change() * 100
    return annual.dropna(subset=["growth"]).reset_index()[["year", "growth"]]


def _error_shade(value) -> str:
    """Diverging red/blue background for a forecast error cell, shading up to
    a 2pp miss. Hand-rolled rather than Styler.background_gradient because
    that pulls in matplotlib, which this project does not otherwise depend
    on — the same reason the monitor's GDP detail tables style with plain CSS
    strings."""
    if value is None or pd.isna(value):
        return ""
    alpha = min(abs(float(value)) / 2.0, 1.0) * 0.55
    if alpha < 0.02:
        return ""
    rgb = "192,0,0" if value > 0 else "0,112,192"  # optimistic red / pessimistic blue
    return f"background-color: rgba({rgb},{alpha:.2f})"


def outturn_section(df: pd.DataFrame):
    st.title("Forecast vs Outturn")
    st.caption(
        "Every GDP growth forecast plotted against what actually happened, "
        "using realized annual growth computed from the monitor's own "
        "quarterly NESDC series. Only years with four published quarters "
        "are scored."
    )
    outturn = _annual_gdp_growth()
    if outturn.empty:
        st.warning(
            "Reference GDP series not available — "
            "`data/reference/gdp.csv` is missing or empty."
        )
        return
    fc = pio.forecasts_only(df)
    fc = fc[fc["indicator"] == "gdp_growth"]
    if fc.empty:
        st.warning("No GDP growth forecasts on file yet.")
        return

    scored = pio.latest_vintage(fc).merge(
        outturn, left_on="target_year", right_on="year", how="inner")
    if scored.empty:
        st.info(
            "No overlap yet between forecast target years and completed "
            "outturn years — this fills in once a forecast year closes out."
        )
        st.dataframe(outturn.tail(10).style.format({"growth": "{:,.2f}"}),
                     width="stretch", hide_index=True)
        return

    scored["error"] = scored["value"] - scored["growth"]
    institutions = sorted(scored["institution"].unique())
    colors = _institution_colors(institutions, df)

    fig = go.Figure()
    years = sorted(scored["target_year"].unique())
    fig.add_trace(go.Scatter(
        x=outturn[outturn["year"].isin(years)]["year"],
        y=outturn[outturn["year"].isin(years)]["growth"],
        mode="lines+markers", name="Outturn",
        line=dict(color=TOTAL_COLOR, width=2.5), marker=dict(size=8),
        hovertemplate="outturn %{y:,.2f}%<extra></extra>",
    ))
    for inst in institutions:
        sub = scored[scored["institution"] == inst]
        fig.add_trace(go.Scatter(
            x=sub["target_year"], y=sub["value"], mode="markers", name=inst,
            marker=dict(size=9, symbol="diamond", color=colors.get(inst, PALETTE[2])),
            hovertemplate="%{y:,.2f}%<extra>" + inst + "</extra>",
        ))
    fig.update_layout(
        title=dict(text="GDP growth — final forecast vs outturn", font_size=14),
        height=440, margin=dict(l=10, r=10, t=44, b=10), font=font(),
        xaxis=axis(title="target year", dtick=1), yaxis=axis(title="%", zeroline=True),
        plot_bgcolor="white", paper_bgcolor="white", legend=legend_bottom(),
    )
    st.plotly_chart(fig, width="stretch", key="out_chart")

    st.subheader("Forecast error by institution")
    st.caption("Forecast minus outturn, in percentage points. Positive = too optimistic.")
    err = scored.pivot_table(index="institution", columns="target_year",
                             values="error", aggfunc="last")
    year_cols = list(err.columns)
    err["Mean error"] = err[year_cols].mean(axis=1)
    err["Mean abs. error"] = scored.groupby("institution")["error"].apply(
        lambda s: s.abs().mean())
    err.columns = [str(c) for c in err.columns]
    st.dataframe(
        err.style.format("{:+,.2f}", na_rep="—").map(
            _error_shade, subset=[str(c) for c in year_cols]),
        width="stretch",
    )
    _download(scored[["institution", "target_year", "value", "growth", "error"]],
              "forecast_vs_outturn.csv", "dl_out")


# ── Detail comparison ─────────────────────────────────────────────────────────
def _ordered_institutions(df: pd.DataFrame) -> list[str]:
    """Expected institutions in registry order (official, then international,
    then bank), followed by anything else present in the data. Expected-but-
    absent forecasters stay in the list so the table shows them as a gap."""
    expected = [name for name, _ in pio.EXPECTED_INSTITUTIONS]
    extra = sorted(set(df["institution"].dropna()) - set(expected)) if not df.empty else []
    return expected + extra


def _base_year_actuals(df: pd.DataFrame, base_year: int) -> dict:
    """One outturn value per indicator for the base year. Agencies restate
    the base slightly differently, so this prefers NESDC — the national
    accounts compiler — and falls back to whoever else published it."""
    actual = df[(df["kind"] == "actual") & (df["target_year"] == base_year)]
    if actual.empty:
        return {}
    preferred = [n for n, _ in pio.EXPECTED_INSTITUTIONS]
    rank = {name: i for i, name in enumerate(preferred)}
    actual = actual.assign(_rank=actual["institution"].map(rank).fillna(len(rank)))
    best = actual.sort_values(["_rank", "vintage"]).groupby("indicator").head(1)
    return dict(zip(best["indicator"], best["value"]))


def detail_comparison_section(df: pd.DataFrame):
    st.title("Detail Comparison")
    st.caption(
        "Every forecaster's full projection detail side by side, current year "
        "and next year in one table. Each column is that institution's most "
        "recent published round — the dates differ, so read it as a snapshot "
        "of published views, not a single-date survey."
    )

    years = sorted(int(y) for y in df["target_year"].dropna().unique())
    fdf = pio.forecasts_only(df)
    forecast_years = sorted(int(y) for y in fdf["target_year"].dropna().unique())
    institutions = _ordered_institutions(df)
    latest = pio.latest_vintage(fdf)

    c1, c2 = st.columns([1, 3])
    with c1:
        current_year = st.selectbox(
            "Current year", forecast_years or years,
            index=0, key="det_year",
        )
    next_year = current_year + 1
    base_year = current_year - 1
    with c2:
        hide_empty = st.toggle(
            "Hide agencies with no data", value=False, key="det_hide",
            help="Off by default: an expected forecaster we have not loaded "
                 "yet should read as a visible gap, not vanish from the table.",
        )

    shares = pio.gdp_shares()
    actuals = _base_year_actuals(df, base_year)

    sel = latest[latest["target_year"].isin([current_year, next_year])]
    values = {(int(r["target_year"]), r["institution"], r["indicator"]): r["value"]
              for _, r in sel.iterrows()}
    approx = {(int(r["target_year"]), r["institution"], r["indicator"]): bool(r["vintage_approx"])
              for _, r in sel.iterrows()}

    agencies = institutions
    if hide_empty:
        agencies = [a for a in institutions
                    if any((y, a, i) in values for y in (current_year, next_year)
                           for i in pio.INDICATORS)]
    if not agencies:
        st.info("No forecaster on file has published for these years yet.")
        return

    rows = []
    for key in pio.INDICATORS:
        vals, stale = {}, {}
        for year in (current_year, next_year):
            for agency in agencies:
                vals[(year, agency)] = values.get((year, agency, key))
                stale[(year, agency)] = approx.get((year, agency, key), False)
        rows.append({
            "label": pio.indicator_label(key),
            "decimals": pio.indicator_decimals(key),
            "main": key in pio.MAIN_ROWS,
            "share": shares.get(key),
            "actual": actuals.get(key),
            "values": vals,
            "stale": stale,
        })

    st.markdown(
        projections_table_html.build_detail_table_html(
            rows, agencies, current_year, next_year, base_year),
        unsafe_allow_html=True,
    )

    as_of = []
    for agency in agencies:
        sub = latest[latest["institution"] == agency]
        if sub.empty:
            continue
        vintage = sub["vintage"].max()
        star = "*" if bool(sub[sub["vintage"] == vintage]["vintage_approx"].any()) else ""
        as_of.append(f"**{agency}** {vintage:%d %b %Y}{star}")
    if as_of:
        st.caption("As of — " + " · ".join(as_of))

    notes = [
        f"`{base_year}` column is the outturn as published by the highest-priority "
        "agency reporting it (NESDC first) — agencies restate the base year "
        "slightly differently.",
        "`Share of GDP` is computed from the monitor's own national accounts "
        "(`data/reference/gdp_expenditure_share.csv`), latest year available.",
    ]
    if any(r["stale"].get(k) for r in rows for k in r["stale"]):
        notes.append(
            "Greyed values come from a round whose exact publication date the "
            "source does not state (marked `*` above) — round ordering is "
            "correct, the exact day is not."
        )
    missing = [a for a in agencies if a not in set(df["institution"])]
    if missing:
        notes.append(
            "**Not loaded yet:** " + ", ".join(missing)
            + " — declared in `EXPECTED_INSTITUTIONS` so they stay visible as "
            "gaps rather than dropping silently out of the comparison."
        )
    st.caption("  \n".join("· " + n for n in notes))

    flat = []
    for row in rows:
        rec = {"indicator": row["label"], "share_of_gdp": row["share"],
               f"{base_year}_actual": row["actual"]}
        for (year, agency), value in row["values"].items():
            rec[f"{year} {agency}"] = value
        flat.append(rec)
    _download(pd.DataFrame(flat), f"forecast_detail_{current_year}_{next_year}.csv",
              "dl_detail")

    st.markdown("---")
    st.subheader(f"GDP growth — {current_year} vs {next_year}")
    fig = go.Figure()
    for year, color in ((current_year, PALETTE[0]), (next_year, PALETTE[3])):
        sub = latest[(latest["target_year"] == year) & (latest["indicator"] == "gdp_growth")]
        sub = sub.set_index("institution").reindex(agencies).dropna(subset=["value"])
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x=list(sub.index), y=sub["value"], name=str(year), marker_color=color,
            hovertemplate="%{y:,.2f}%<extra>" + str(year) + "</extra>",
        ))
    fig.update_layout(
        barmode="group", height=420, margin=dict(l=10, r=10, t=30, b=10), font=font(),
        xaxis=axis(), yaxis=axis(title="%", zeroline=True),
        plot_bgcolor="white", paper_bgcolor="white", legend=legend_bottom(),
    )
    st.plotly_chart(fig, width="stretch", key="det_gdp_chart")


# ── Data & sources ────────────────────────────────────────────────────────────
def data_section(df: pd.DataFrame):
    st.title("Data & Sources")
    st.caption(
        "The whole forecast table, exactly as it sits in "
        "`data/projections/gdp_forecasts.csv`. Hand-maintained: published "
        "forecasts arrive as PDFs and press conferences, so nothing fetches "
        "this automatically."
    )
    problems = pio.validate(df)
    if problems:
        st.error("**Validation problems** — fix these in the CSV:\n\n"
                 + "\n".join(f"- {p}" for p in problems))
    else:
        st.success("Forecast table validates cleanly.")

    if df.empty:
        _no_data_notice()
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Institutions", f"{df['institution'].nunique()}")
    c3.metric("Latest vintage", f"{df['vintage'].max():%d %b %Y}")

    show = df.copy()
    show["vintage"] = show["vintage"].dt.strftime("%Y-%m-%d")
    show["indicator"] = show["indicator"].map(pio.indicator_label).fillna(show["indicator"])
    st.dataframe(
        show, width="stretch", hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("source_url", display_text="Open ↗"),
        },
    )
    _download(df, "thailand_growth_forecasts.csv", "dl_all")

    st.markdown("---")
    st.subheader("Adding a new forecast round")
    st.markdown(
        "- Append a row per indicator — **never edit a past vintage**, or the "
        "revision charts lose their history.\n"
        "- `vintage` is the publication date of that round; `target_year` is "
        "the year being forecast.\n"
        "- Where an institution publishes a band rather than a point, put the "
        "central value in `value` and the bounds in `low`/`high`.\n"
        "- Set `kind` to `actual` for a base-year row restating that agency's "
        "own outturn, so it is never scored as a forecast.\n"
        "- Set `vintage_approx` to `true` when the source names the round but "
        "not an exact date.\n"
        "- Run `python scripts/check_projections.py` before committing."
    )


# ── Sidebar & routing ─────────────────────────────────────────────────────────
st.sidebar.title("📈 Growth Projections")
st.sidebar.caption("Thailand · forecasts, revisions and consensus")

df = _load()

section = st.sidebar.radio(
    "View",
    ["Detail Comparison", "Forecast Comparison", "Forecast Revisions",
     "Consensus & Dispersion", "Forecast vs Outturn", "Data & Sources"],
)

if df.empty and section != "Data & Sources":
    st.title(section)
    _no_data_notice()
else:
    if section == "Detail Comparison":
        detail_comparison_section(df)
    elif section == "Forecast Comparison":
        comparison_section(df)
    elif section == "Forecast Revisions":
        revisions_section(df)
    elif section == "Consensus & Dispersion":
        consensus_section(df)
    elif section == "Forecast vs Outturn":
        outturn_section(df)
    elif section == "Data & Sources":
        data_section(df)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Hand-maintained forecast table — see `data/projections/README.md` "
    "for how to add a new round."
)
