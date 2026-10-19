#!/usr/bin/env python3
"""GA4: which pages and channels make money (all traffic, not only organic).

Run with the claude-seo virtual environment, which has the GA4 library:
    "%USERPROFILE%/.claude/skills/seo/.venv/Scripts/python.exe" ga4_money_pages.py --property properties/123 --days 90 --json

Reports (one GA4 Data API call each):
    channels      sessions, engaged sessions and key events by default channel group
    events        every event name with its count and key-event count
    landing_pages sessions and key events by landing page
    key_event_pages  key events by page path and event name (where conversions happen)
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
        DateRange, Dimension, Filter, FilterExpression, Metric, NumericValue, OrderBy, RunReportRequest,
    )
    from google_auth import get_oauth_credentials
except ImportError as exc:
    print(json.dumps({"error": f"Run this with the claude-seo .venv python ({exc})"}))
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def run(client, prop, days, dims, mets, order_metric, limit=100, key_events_only=False):
    req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="yesterday")],
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in mets],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=True)],
        limit=limit,
    )
    if key_events_only:
        req.metric_filter = FilterExpression(filter=Filter(
            field_name="keyEvents",
            numeric_filter=Filter.NumericFilter(operation=Filter.NumericFilter.Operation.GREATER_THAN,
                                                value=NumericValue(double_value=0))))
    resp = client.run_report(req)
    rows = []
    for r in resp.rows:
        row = {d: v.value for d, v in zip(dims, r.dimension_values)}
        for m, v in zip(mets, r.metric_values):
            row[m] = float(v.value) if "." in v.value else int(v.value)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--property", required=True)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    prop = args.property if args.property.startswith("properties/") else f"properties/{args.property}"

    creds = get_oauth_credentials(SCOPES)
    if not creds:
        print(json.dumps({"error": "No Google credentials (service account) configured"}))
        sys.exit(1)
    client = BetaAnalyticsDataClient(credentials=creds)

    out = {"property": prop, "days": args.days}
    try:
        out["channels"] = run(client, prop, args.days, ["sessionDefaultChannelGroup"],
                              ["sessions", "engagedSessions", "keyEvents", "totalUsers"], "sessions")
        out["events"] = run(client, prop, args.days, ["eventName"], ["eventCount", "keyEvents"], "eventCount")
        out["landing_pages"] = run(client, prop, args.days, ["landingPage"],
                                   ["sessions", "engagedSessions", "keyEvents"], "sessions", limit=50)
        out["key_event_pages"] = run(client, prop, args.days, ["pagePath", "eventName"],
                                     ["keyEvents"], "keyEvents", limit=50, key_events_only=True)
        out["error"] = None
    except Exception as exc:  # report API errors as data, not a crash
        out["error"] = str(exc)[:500]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
