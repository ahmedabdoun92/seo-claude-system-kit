#!/usr/bin/env python3
"""GA4: counts of chosen events for a date range, in total and by page.

Run with the claude-seo virtual environment (it has the GA4 library):
    "%USERPROFILE%/.claude/skills/seo/.venv/Scripts/python.exe" ga4_events.py \
        --property properties/123 --start 2026-10-06 --end 2026-10-12 \
        --events whatsapp_click,phone_click,generate_lead --json

Also returns sessions by default channel group for the same range.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.path.expanduser("~/.claude/skills/seo/scripts"))))
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, FilterExpressionList, Metric, RunReportRequest,
    )
    from google_auth import get_oauth_credentials
except ImportError as exc:
    print(json.dumps({"error": f"Run this with the claude-seo .venv python ({exc})"}))
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--property", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--events", required=True, help="comma-separated event names")
    ap.add_argument("--host", help="only count events on this hostname (e.g. www.example.com)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    prop = a.property if a.property.startswith("properties/") else f"properties/{a.property}"
    events = [e.strip() for e in a.events.split(",") if e.strip()]

    creds = get_oauth_credentials(["https://www.googleapis.com/auth/analytics.readonly"])
    if not creds:
        print(json.dumps({"error": "No Google credentials configured"}))
        sys.exit(1)
    client = BetaAnalyticsDataClient(credentials=creds)
    rng = [DateRange(start_date=a.start, end_date=a.end)]
    only_events = FilterExpression(filter=Filter(field_name="eventName",
                                                 in_list_filter=Filter.InListFilter(values=events)))
    if a.host:  # leave out tests from localhost and previews
        only_host = FilterExpression(filter=Filter(field_name="hostName",
                                                   string_filter=Filter.StringFilter(value=a.host)))
        only_events = FilterExpression(and_group=FilterExpressionList(expressions=[only_events, only_host]))
    out = {"property": prop, "start": a.start, "end": a.end, "events": {e: 0 for e in events},
           "by_page": [], "channels": [], "error": None}
    try:
        r = client.run_report(RunReportRequest(property=prop, date_ranges=rng,
                                               dimensions=[Dimension(name="eventName"), Dimension(name="pagePath")],
                                               metrics=[Metric(name="eventCount")], dimension_filter=only_events, limit=500))
        for row in r.rows:
            ev, page, n = row.dimension_values[0].value, row.dimension_values[1].value, int(row.metric_values[0].value)
            out["events"][ev] = out["events"].get(ev, 0) + n
            out["by_page"].append({"event": ev, "page": page, "count": n})
        r = client.run_report(RunReportRequest(property=prop, date_ranges=rng,
                                               dimensions=[Dimension(name="sessionDefaultChannelGroup")],
                                               metrics=[Metric(name="sessions"), Metric(name="engagedSessions")]))
        out["channels"] = [{"channel": x.dimension_values[0].value, "sessions": int(x.metric_values[0].value),
                            "engaged": int(x.metric_values[1].value)} for x in r.rows]
    except Exception as exc:  # API errors become data
        out["error"] = str(exc)[:400]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
