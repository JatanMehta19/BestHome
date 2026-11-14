"""
============================================================
 Commute Cost Ranker - settings loader
============================================================
 Resolves configuration in one place so no script carries a
 personal value in its source:

     config.py          your real settings  (gitignored)
     config_example.py  placeholder defaults (committed)

 Import from here, never from config directly:

     from settings import OFFICE_COORDS, CLOSE_BUDGET
============================================================
"""
import sys

try:
    import config as _cfg
    USING_EXAMPLE_CONFIG = False
except ModuleNotFoundError:
    import config_example as _cfg
    USING_EXAMPLE_CONFIG = True

_NAMES = [
    "OFFICE_COORDS",
    "CLOSE_TOWNS", "CLOSE_BUDGET", "FAR_TOWNS", "FAR_BUDGET",
    "MIN_BEDS", "MIN_BATHS",
    "START_URLS", "END_PAGE", "MAX_ITEMS",
    "COMMUTE_DAYS_PER_WEEK", "WORK_WEEKS_PER_YEAR",
    "MORTGAGE_RATE", "MORTGAGE_TERM_YEARS", "DOWN_PAYMENT_PCT",
    "GAS_PRICE_PER_GALLON", "CAR_MPG", "UTILITY_EST_MONTHLY",
    "WEIGHT_PRICE_SQFT", "WEIGHT_TOTAL_MONTHLY",
    "WEIGHT_COMMUTE_MINS", "WEIGHT_LIRR",
    "LIRR_PENALTY_MINS", "TOP_N",
]

# A key missing from a hand-edited config.py falls back to the example value
# rather than crashing three scripts deep.
import config_example as _fallback
_missing = []
for _name in _NAMES:
    if hasattr(_cfg, _name):
        globals()[_name] = getattr(_cfg, _name)
    else:
        globals()[_name] = getattr(_fallback, _name)
        _missing.append(_name)

OFFICE_LAT, OFFICE_LON = OFFICE_COORDS

# Shared paths
RAW_FILE    = "output/raw_listings.json"
CLEAN_FILE  = "output/listings_clean.csv"
SCORED_FILE = "output/listings_scored.csv"
REPORT_FILE = "output/top_listings_report.txt"


def banner():
    """Print once at the top of each script, so it is obvious which config ran."""
    if USING_EXAMPLE_CONFIG:
        print("  config.py not found - running on config_example.py placeholders.")
        print("  Copy config_example.py to config.py and set your own values.")
    if _missing:
        print("  config.py is missing " + str(len(_missing)) +
              " key(s), using example values: " + ", ".join(_missing))


if __name__ == "__main__":
    banner()
    print("  office    " + str(OFFICE_COORDS))
    print("  budgets   close " + format(CLOSE_BUDGET, ",") +
          " / far " + format(FAR_BUDGET, ","))
    print("  minimums  " + str(MIN_BEDS) + "bd / " + str(MIN_BATHS) + "ba")
    sys.exit(0)
