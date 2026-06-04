#!/usr/bin/env python3
"""
build_index.py — regenerate index.html for the aml-reports GitHub Pages site.

Required by the github-pages-report-publishing skill (Section 5).

Scans CLONE_PATH for *.html (excluding index.html), reads each file's <title>,
and writes a styled index.html listing reports newest-first (by file mtime).

Title convention parsed:
    "<TICKER> — <Company> · <Kind> · <Engine/version>"
    e.g. "PL — Planet Labs PBC · Quick Trade · Equity Research Engine v4.10"

If a report's <title> does not match this convention, the raw title (or the
filename) is shown as the report name and the optional columns are left blank.

Usage:
    python3 scripts/build_index.py "<CLONE_PATH>"
    # CLONE_PATH defaults to the parent of this script's directory.
"""

import sys
import os
import re
import html
import datetime

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def read_title(path):
    """Return the <title> text of an HTML file, or '' if none found."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return ""
    m = TITLE_RE.search(text)
    if not m:
        return ""
    return html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())


def parse_title(title):
    """
    Split "<TICKER> — <Company> · <Kind> · <Engine/version>" into parts.
    Returns dict with ticker, company, kind, engine. Missing parts -> "".
    Accepts em-dash (—) or hyphen for the TICKER separator, and middle-dot (·)
    as the field separator.
    """
    ticker = company = kind = engine = ""
    if not title:
        return {"ticker": "", "company": "", "kind": "", "engine": ""}

    # Split off the ticker on the first em-dash (or " - ").
    rest = title
    m = re.match(r"\s*([^—]+?)\s*—\s*(.*)$", title)
    if m:
        ticker, rest = m.group(1).strip(), m.group(2).strip()
    else:
        m = re.match(r"\s*(\S+)\s+-\s+(.*)$", title)
        if m:
            ticker, rest = m.group(1).strip(), m.group(2).strip()

    # Remaining fields separated by middle dot.
    parts = [p.strip() for p in rest.split("·")] if rest else []
    if len(parts) >= 1:
        company = parts[0]
    if len(parts) >= 2:
        kind = parts[1]
    if len(parts) >= 3:
        engine = " · ".join(parts[2:]).strip()

    return {"ticker": ticker, "company": company, "kind": kind, "engine": engine}


def collect_reports(clone_path):
    """Return list of report dicts, newest-first by mtime."""
    reports = []
    for name in os.listdir(clone_path):
        if not name.lower().endswith(".html"):
            continue
        if name.lower() == "index.html":
            continue
        full = os.path.join(clone_path, name)
        if not os.path.isfile(full):
            continue
        mtime = os.path.getmtime(full)
        title = read_title(full)
        parsed = parse_title(title)
        reports.append(
            {
                "filename": name,
                "mtime": mtime,
                "date": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                "title": title,
                "display": title or name,
                **parsed,
            }
        )
    reports.sort(key=lambda r: r["mtime"], reverse=True)
    return reports


def render_index(reports):
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for r in reports:
        ticker = html.escape(r["ticker"])
        company = html.escape(r["company"] or r["display"])
        kind = html.escape(r["kind"])
        engine = html.escape(r["engine"])
        fname = html.escape(r["filename"])
        date = html.escape(r["date"])
        rows.append(
            f"""      <li class="report">
        <a class="report-link" href="./{fname}">
          <span class="ticker">{ticker or "&nbsp;"}</span>
          <span class="company">{company}</span>
        </a>
        <span class="meta">
          <span class="kind">{kind}</span>
          <span class="engine">{engine}</span>
          <span class="date">{date}</span>
        </span>
      </li>"""
        )

    if not rows:
        rows_html = '      <li class="empty">No reports yet.</li>'
    else:
        rows_html = "\n".join(rows)

    count = len(reports)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AML Reports</title>
<style>
  :root {{
    --bg: #0f1115;
    --card: #171a21;
    --ink: #e8ebf0;
    --muted: #9aa3b0;
    --accent: #5b9dff;
    --line: #242935;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 48px 20px 80px; }}
  header h1 {{ margin: 0 0 4px; font-size: 28px; letter-spacing: -0.01em; }}
  header p {{ margin: 0; color: var(--muted); font-size: 14px; }}
  ul {{ list-style: none; margin: 32px 0 0; padding: 0; }}
  .report {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px 16px;
  }}
  .report-link {{
    text-decoration: none;
    color: var(--ink);
    display: flex;
    align-items: baseline;
    gap: 10px;
    flex: 1 1 auto;
    min-width: 0;
  }}
  .report-link:hover .company {{ text-decoration: underline; }}
  .ticker {{
    color: var(--accent);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    flex: 0 0 auto;
  }}
  .company {{ font-weight: 600; overflow-wrap: anywhere; }}
  .meta {{
    display: flex;
    gap: 12px;
    align-items: baseline;
    color: var(--muted);
    font-size: 13px;
    flex: 0 0 auto;
  }}
  .kind {{ color: var(--ink); opacity: 0.85; }}
  .engine {{ opacity: 0.7; }}
  .date {{ font-variant-numeric: tabular-nums; }}
  .empty {{ color: var(--muted); padding: 24px; text-align: center; }}
  footer {{ margin-top: 40px; color: var(--muted); font-size: 12px; }}
  @media (max-width: 560px) {{
    .report {{ flex-direction: column; }}
    .meta {{ font-size: 12px; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AML Reports</h1>
      <p>{count} report{"" if count == 1 else "s"} · generated {generated}</p>
    </header>
    <ul>
{rows_html}
    </ul>
    <footer>AutoMagic Labs · published via GitHub Pages</footer>
  </div>
</body>
</html>
"""


def main():
    clone_path = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    clone_path = os.path.abspath(clone_path)
    if not os.path.isdir(clone_path):
        sys.stderr.write(f"error: clone path not found: {clone_path}\n")
        sys.exit(1)

    reports = collect_reports(clone_path)
    out = os.path.join(clone_path, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_index(reports))
    print(f"wrote {out} ({len(reports)} report(s))")


if __name__ == "__main__":
    main()
