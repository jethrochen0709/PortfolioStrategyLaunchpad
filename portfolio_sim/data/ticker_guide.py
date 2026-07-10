"""
Static reference list of well-known tickers, grouped by category, shown in
the app as a quick lookup for people picking tickers to backtest with. This
is just a reference guide - it doesn't affect the backtest engine at all.
"""

TICKER_GUIDE = {
    "US total market": [
        ("VTI", "Vanguard Total Stock Market ETF"),
        ("ITOT", "iShares Core S&P Total US Stock Market ETF"),
        ("SCHB", "Schwab US Broad Market ETF"),
    ],
    "S&P 500": [
        ("SPY", "SPDR S&P 500 ETF Trust (oldest, most liquid)"),
        ("VOO", "Vanguard S&P 500 ETF"),
        ("IVV", "iShares Core S&P 500 ETF"),
    ],
    "Nasdaq / tech-heavy": [
        ("QQQ", "Invesco QQQ Trust - tracks the Nasdaq-100"),
        ("QQQM", "Invesco Nasdaq-100 ETF - lower-cost QQQ twin"),
    ],
    "US small / mid cap": [
        ("IWM", "iShares Russell 2000 ETF - small cap"),
        ("VB", "Vanguard Small-Cap ETF"),
        ("MDY", "SPDR S&P MidCap 400 ETF"),
    ],
    "International (developed)": [
        ("VEA", "Vanguard FTSE Developed Markets ETF"),
        ("EFA", "iShares MSCI EAFE ETF (Europe, Australasia, Far East)"),
        ("SCHF", "Schwab International Equity ETF"),
    ],
    "International (emerging markets)": [
        ("VWO", "Vanguard FTSE Emerging Markets ETF"),
        ("IEMG", "iShares Core MSCI Emerging Markets ETF"),
        ("EEM", "iShares MSCI Emerging Markets ETF"),
    ],
    "Total world / global": [
        ("VT", "Vanguard Total World Stock ETF"),
        ("VXUS", "Vanguard Total International Stock ETF (ex-US)"),
        ("ACWI", "iShares MSCI ACWI ETF"),
    ],
    "Bonds / fixed income": [
        ("BND", "Vanguard Total Bond Market ETF"),
        ("AGG", "iShares Core US Aggregate Bond ETF"),
        ("TLT", "iShares 20+ Year Treasury Bond ETF (long duration)"),
        ("IEF", "iShares 7-10 Year Treasury Bond ETF"),
        ("SHY", "iShares 1-3 Year Treasury Bond ETF (short duration)"),
        ("TIP", "iShares TIPS Bond ETF (inflation-protected)"),
    ],
    "Dividend / value": [
        ("VYM", "Vanguard High Dividend Yield ETF"),
        ("SCHD", "Schwab US Dividend Equity ETF"),
        ("VTV", "Vanguard Value ETF"),
    ],
    "Growth": [
        ("VUG", "Vanguard Growth ETF"),
        ("IWF", "iShares Russell 1000 Growth ETF"),
    ],
    "Gold / commodities": [
        ("GLD", "SPDR Gold Shares"),
        ("IAU", "iShares Gold Trust"),
        ("DBC", "Invesco DB Commodity Index Tracking Fund"),
    ],
    "Real estate": [
        ("VNQ", "Vanguard Real Estate ETF (REITs)"),
        ("SCHH", "Schwab US REIT ETF"),
    ],
    "Popular individual stocks": [
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("NVDA", "NVIDIA"),
        ("AMZN", "Amazon"),
        ("GOOGL", "Alphabet / Google"),
        ("META", "Meta Platforms"),
        ("TSLA", "Tesla"),
        ("BRK-B", "Berkshire Hathaway (class B)"),
        ("JPM", "JPMorgan Chase"),
        ("JNJ", "Johnson & Johnson"),
    ],
}


def all_guide_tickers():
    """Flat list of every ticker in the guide, for quick membership checks."""
    return [ticker for rows in TICKER_GUIDE.values() for ticker, _ in rows]
