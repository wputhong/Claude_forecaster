"""Consistency check: the growth-projection forecast table must be well-formed.

data/projections/gdp_forecasts.csv is hand-maintained — published forecasts
arrive as PDFs and press conferences, not as a feed — so the usual protection
of a parser rejecting bad input does not apply here. A typo lands straight on
the dashboard.

The failure modes that matter are silent ones:

  * An unknown `indicator` key drops the row out of every chart. It is still
    in the file, so it looks maintained, but the picker never offers it.
  * A duplicated (institution, vintage, target_year, indicator) key makes the
    "latest vintage" pick arbitrary — two different numbers claim to be the
    same forecast, and which one wins depends on row order.
  * An overwritten vintage (rather than an appended one) erases revision
    history, which is the one thing this dashboard exists to show. That can't
    be detected after the fact, which is why the README leads with it.
  * A low/high band that does not bracket its own point forecast draws a
    range marker that contradicts the dot sitting next to it.

Run: python scripts/check_projections.py   (exits 1 on problems)
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parent.parent

# projections_io pulls streamlit for @st.cache_data. Stub it so this check
# needs neither streamlit installed nor a script run context.
if "streamlit" not in sys.modules:
    _st = types.ModuleType("streamlit")
    _st.cache_data = lambda **kwargs: (lambda fn: fn)
    sys.modules["streamlit"] = _st

sys.path.insert(0, str(ROOT))

import projections_io  # noqa: E402


def main() -> int:
    path = projections_io.FORECASTS_CSV
    if not path.exists():
        print(f"✗ missing forecast table: {path.relative_to(ROOT)}")
        return 1

    df = projections_io.load_forecasts(path)
    problems = projections_io.validate(df)
    if problems:
        print(f"✗ {len(problems)} problem(s) in {path.relative_to(ROOT)}:")
        for p in problems:
            print(f"  - {p}")
        return 1

    if df.empty:
        print(f"✓ {path.relative_to(ROOT)} is well-formed (no forecast rows yet)")
    else:
        print(
            f"✓ {path.relative_to(ROOT)}: {len(df)} rows, "
            f"{df['institution'].nunique()} institutions, "
            f"{df['indicator'].nunique()} indicators, "
            f"latest vintage {df['vintage'].max():%Y-%m-%d}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
