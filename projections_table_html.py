"""
Renders the cross-agency forecast detail table as a styled HTML string for
st.markdown(html, unsafe_allow_html=True).

A two-row header (year block, then one column per agency under it), a
share-of-GDP column and a base-year outturn column, then every forecaster's
projection side by side — the layout of the working spreadsheet this view
replaces. Styling deliberately mirrors summary_table_html.py so the two
tables read as the same family.

st.dataframe cannot express this: it has no grouped column headers, so the
year blocks would collapse into flat "2026 · BOT" strings, and it cannot
band rows by whether an indicator is a main aggregate or a sub-component.
"""
import html

HEADER_BLUE = "#1F4E78"
NEXT_YEAR_BLUE = "#2E6DA4"
AGENCY_BAND = "#DCE6F1"
BORDER_GRAY = "#BFBFBF"
MAIN_ROW_GRAY = "#EDEDED"
SHARE_GRAY = "#F5F5F5"
ACTUAL_BLUE = "#EAF1F8"

CSS = f"""
<style>
.proj-detail-wrap {{ overflow-x: auto; }}
table.proj-detail {{ border-collapse: collapse; font-size: 12px; width: 100%;
  font-family: -apple-system, "Segoe UI", Arial, sans-serif; }}
table.proj-detail th, table.proj-detail td {{
  border-right: 1px solid {BORDER_GRAY}; padding: 3px 7px;
  text-align: right; white-space: nowrap; }}
table.proj-detail td.label, table.proj-detail th.label {{ text-align: left; white-space: pre; }}
table.proj-detail thead tr.year-row th {{ background: {HEADER_BLUE}; color: #fff;
  font-weight: 700; border-bottom: 2px solid #fff; text-align: center; }}
table.proj-detail thead tr.year-row th.next {{ background: {NEXT_YEAR_BLUE}; }}
table.proj-detail thead tr.agency-row th {{ background: {AGENCY_BAND}; color: #1A1A1A;
  font-weight: 700; text-align: center; }}
table.proj-detail tbody tr.main td {{ background: {MAIN_ROW_GRAY}; font-weight: 700; }}
table.proj-detail tbody tr:hover td {{ background: #F0F4F8; }}
table.proj-detail td.share {{ background: {SHARE_GRAY}; color: #555; }}
table.proj-detail td.actual {{ background: {ACTUAL_BLUE}; }}
table.proj-detail td.yearsep, table.proj-detail th.yearsep {{ border-left: 2px solid #1A1A1A; }}
table.proj-detail td.stale {{ color: #9A9A9A; }}
table.proj-detail td.empty {{ background: #FCFCFC; }}
table.proj-detail th.noagency, table.proj-detail td.noagency {{
  background: #F7F7F7; color: #9A9A9A; font-weight: 400;
  max-width: 78px; overflow: hidden; text-overflow: ellipsis; font-size: 11px; }}
</style>
"""


def _fmt(value, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:,.{decimals}f}"


def build_detail_table_html(rows: list, agencies: list, current_year: int,
                            next_year: int, base_year: int) -> str:
    """`rows` is a list of dicts:
        label, decimals, main (bool), share (float|None),
        actual (float|None), values {(year, agency): float|None},
        stale {(year, agency): bool}
    `agencies` is the column order, repeated under each year block.
    """
    n = len(agencies)
    year_cells = (
        '<th class="label"></th><th>Share of GDP</th>'
        f'<th>{base_year}</th>'
        f'<th class="yearsep" colspan="{n}">{current_year}</th>'
        f'<th class="next yearsep" colspan="{n}">{next_year}</th>'
    )
    # An agency with no value anywhere is still shown, but compressed.
    empty_agencies = {
        a for a in agencies
        if not any(r["values"].get((y, a)) is not None
                   for r in rows for y in (current_year, next_year))
    }
    agency_cells = ['<th class="label"></th>', "<th></th>", "<th>actual</th>"]
    for _block in (0, 1):
        for i, a in enumerate(agencies):
            classes = (["yearsep"] if i == 0 else []) + (["noagency"] if a in empty_agencies else [])
            cls = f' class="{" ".join(classes)}"' if classes else ""
            agency_cells.append(f"<th{cls}>{html.escape(a)}</th>")
    thead = (
        "<thead>"
        f'<tr class="year-row">{year_cells}</tr>'
        f'<tr class="agency-row">{"".join(agency_cells)}</tr>'
        "</thead>"
    )

    body = []
    for row in rows:
        dec = row["decimals"]
        indent = "" if row["main"] else "    "
        tr_cls = "main" if row["main"] else "sub"
        cells = [f'<td class="label">{indent}{html.escape(row["label"])}</td>']
        share = row.get("share")
        cells.append(f'<td class="share">{"" if share is None else f"{share:,.0f}%"}</td>')
        cells.append(f'<td class="actual">{_fmt(row.get("actual"), dec)}</td>')
        for year in (current_year, next_year):
            for i, agency in enumerate(agencies):
                value = row["values"].get((year, agency))
                classes = []
                if i == 0:
                    classes.append("yearsep")
                if row.get("stale", {}).get((year, agency)):
                    classes.append("stale")
                if agency in empty_agencies:
                    classes.append("noagency")
                elif value is None:
                    classes.append("empty")
                cls = f' class="{" ".join(classes)}"' if classes else ""
                cells.append(f"<td{cls}>{_fmt(value, dec)}</td>")
        body.append(f'<tr class="{tr_cls}">{"".join(cells)}</tr>')

    tbody = f"<tbody>{''.join(body)}</tbody>"
    return f'{CSS}<div class="proj-detail-wrap"><table class="proj-detail">{thead}{tbody}</table></div>'
