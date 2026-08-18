"""
Shared Plotly chart theme (client style guide) — the 20-color palette, font
and axis defaults, and the time-axis formatter.

Lifted out of app.py so a second Streamlit app (projections_app.py) draws
charts that are pixel-identical to the main monitor's without copying the
helpers. app.py re-binds these under its original private names, so its own
call sites are unchanged.
"""
import pandas as pd
import plotly.graph_objects as go

# 20-color numbered palette (extended from the original 10). Color 1 is
# reserved for total/summary lines and single-series marks; colors 2-20
# assign to categorical series strictly in rank order (2nd category -> color
# 2, 3rd -> color 3, ...), not cycled or reordered — charts needing more
# categories than colors 2-10 provide now draw on 11-20 instead of an
# improvised extension color.
FONT_FAMILY = "Open Sans, sans-serif"
FONT_SIZE = 12

PALETTE = [
    "#002060",  # 1  - dark navy   (total line / single-series mark)
    "#93CDDD",  # 2  - light blue
    "#D9D9D9",  # 3  - light gray
    "#FFC000",  # 4  - gold
    "#C00000",  # 5  - dark red
    "#0070C0",  # 6  - blue
    "#93B2D6",  # 7  - slate blue-gray
    "#ED7D31",  # 8  - orange
    "#548235",  # 9  - green
    "#7030A0",  # 10 - purple
    "#DBEEF4",  # 11 - pale ice blue
    "#C3D69B",  # 12 - light sage green
    "#FF0000",  # 13 - bright red
    "#31859C",  # 14 - dark teal
    "#632423",  # 15 - dark maroon
    "#66FF99",  # 16 - bright mint green
    "#FF3399",  # 17 - pink/magenta
    "#9999FF",  # 18 - light purple/lavender
    "#FEF80C",  # 19 - bright yellow
    "#CC9900",  # 20 - dark gold/mustard
]
TOTAL_COLOR = PALETTE[0]


def font(**overrides) -> dict:
    d = dict(family=FONT_FAMILY, size=FONT_SIZE)
    d.update(overrides)
    return d


def axis(zeroline: bool = False, **overrides) -> dict:
    """Axis defaults per style guide: no border line, no gridlines."""
    d = dict(showgrid=False, showline=False, zeroline=zeroline)
    if zeroline:
        d.update(zerolinecolor="#c3c2b7", zerolinewidth=1)
    d.update(overrides)
    return d


def legend_bottom(**overrides) -> dict:
    d = dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0)
    d.update(overrides)
    return d


def apply_time_xaxis(fig: "go.Figure", **overrides) -> None:
    """Format a time-series chart's x-axis from the actual plotted dates,
    read straight off the figure's own traces after they've been added, so
    it works regardless of how each chart is built. A no-op if the figure
    has no date-like x data (e.g. still empty).

    Quarterly-cadence data (consecutive points ~3 months apart) gets
    "Q1-25"-style tick labels instead of a month name, since "Jan-25" reads
    oddly for a series that only ever has one point per quarter. Anything
    else gets "Mon-YY" (e.g. "Jan-24") ticks. Either way the tick interval —
    every 1/2/4 quarters, or every 3/6/12 months — is chosen from the
    plotted date range so labels stay readable whether a chart shows one
    year or twenty."""
    dates = []
    for trace in fig.data:
        x = getattr(trace, "x", None)
        if x is None:
            continue
        dates.extend(v for v in x if v is not None)
    if not dates:
        return
    parsed = pd.to_datetime(pd.Series(dates), errors="coerce").dropna()
    if parsed.empty:
        return
    span_days = (parsed.max() - parsed.min()).days

    unique_sorted = parsed.drop_duplicates().sort_values()
    median_gap_days = (
        unique_sorted.diff().dt.days.median() if len(unique_sorted) >= 2 else None
    )
    is_quarterly = median_gap_days is not None and 80 <= median_gap_days <= 100

    if is_quarterly:
        step = 1 if span_days <= 400 else (2 if span_days <= 1100 else 4)
        quarters = sorted(unique_sorted.dt.to_period("Q").unique())
        chosen = quarters if step == 1 else [q for q in quarters if (q.quarter - 1) % step == 0]
        fig.update_xaxes(
            tickmode="array",
            tickvals=[q.to_timestamp() for q in chosen],
            ticktext=[f"Q{q.quarter}-{q.year % 100:02d}" for q in chosen],
            **overrides,
        )
        return

    if span_days <= 400:
        dtick = "M3"
    elif span_days <= 1100:
        dtick = "M6"
    else:
        dtick = "M12"
    fig.update_xaxes(tickformat="%b-%y", dtick=dtick, **overrides)
