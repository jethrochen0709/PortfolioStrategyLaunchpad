"""
Well-known historical market events/crashes, used to shade regions on the
comparison chart so you can see how each strategy behaved during them.
Dates are approximate (peak-to-trough for crashes) and U.S.-market-centric.
"""
import pandas as pd

HISTORICAL_EVENTS = [
    {"name": "Black Monday 1987", "start": "1987-10-14", "end": "1987-10-19"},
    {"name": "Dot-com Crash", "start": "2000-03-24", "end": "2002-10-09"},
    {"name": "2008 Financial Crisis", "start": "2007-10-09", "end": "2009-03-09"},
    {"name": "US Debt Ceiling Crisis", "start": "2011-07-22", "end": "2011-08-08"},
    {"name": "2018 Q4 Selloff", "start": "2018-10-03", "end": "2018-12-24"},
    {"name": "COVID-19 Crash", "start": "2020-02-19", "end": "2020-03-23"},
    {"name": "2022 Bear Market", "start": "2022-01-03", "end": "2022-10-12"},
]


def events_in_range(start, end):
    """Return only the events that overlap the given [start, end] date range."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return [
        e for e in HISTORICAL_EVENTS
        if pd.Timestamp(e["end"]) >= start_ts and pd.Timestamp(e["start"]) <= end_ts
    ]
