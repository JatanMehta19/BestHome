"""
============================================================
 Commute Cost Ranker - example configuration
============================================================
 Copy this file to config.py and put YOUR values in it:

     copy config_example.py config.py      (Windows)
     cp   config_example.py config.py      (macOS / Linux)

 config.py is gitignored. Everything personal - where you
 work, what you can spend, which towns you are looking in -
 lives there and never gets committed. The pipeline falls
 back to the placeholder values below if config.py is absent,
 so a fresh clone still runs.

 All values here are illustrative. None of them is anyone's
 actual workplace or budget.
============================================================
"""

# ---- Where you commute to -------------------------------------------------
# Placeholder: Mineola LIRR station, a public transit hub.
# Any lat/lng works. Right-click a spot in Google Maps to copy its coordinates.
OFFICE_COORDS = (40.7493, -73.6409)

# ---- Zones and budgets ----------------------------------------------------
# The premise: you will pay more to live closer. Towns are matched on the
# listing's city field, lowercase.
#
# These lists are illustrative. Note that CLOSE_TOWNS surrounds wherever you
# work, so a published copy of this file would give away roughly where that
# is - which is exactly why the real one lives in config.py and is gitignored.
CLOSE_TOWNS  = {"mineola", "westbury", "franklin square", "valley stream"}
CLOSE_BUDGET = 750_000

FAR_TOWNS    = {"bay shore", "islip", "sayville", "patchogue"}
FAR_BUDGET   = 650_000

# ---- Minimum requirements -------------------------------------------------
MIN_BEDS  = 3
MIN_BATHS = 2

# ---- Commuter rail ---------------------------------------------------------
# Listings report a nearest "commuter rail" stop, whatever the network: LIRR,
# Metra, SEPTA, Caltrain. Station names alone are ambiguous to a geocoder
# ("Riverside Station" exists in several states), so step2 appends this region
# when asking Google for the drive time. Set it to the area you are searching.
STATION_GEOCODE_REGION = "Long Island, NY"

# ---- What to scrape -------------------------------------------------------
# Keep these towns in step with CLOSE_TOWNS / FAR_TOWNS, or listings get
# scraped and then discarded as "wrong_town".
START_URLS = [
    "https://www.homes.com/mineola-ny/",
    "https://www.homes.com/westbury-ny/",
    "https://www.homes.com/franklin-square-ny/",
    "https://www.homes.com/valley-stream-ny/",
    "https://www.homes.com/bay-shore-ny/",
    "https://www.homes.com/islip-ny/",
    "https://www.homes.com/sayville-ny/",
    "https://www.homes.com/patchogue-ny/",
]
END_PAGE  = 5     # pages per search URL
MAX_ITEMS = 1000  # hard cap on listings returned

# ---- Your commute pattern -------------------------------------------------
COMMUTE_DAYS_PER_WEEK = 5
WORK_WEEKS_PER_YEAR   = 50   # drop this for PTO

# ---- Financial assumptions ------------------------------------------------
MORTGAGE_RATE        = 0.0623
MORTGAGE_TERM_YEARS  = 30
DOWN_PAYMENT_PCT     = 0.10
GAS_PRICE_PER_GALLON = 4.00
CAR_MPG              = 28
UTILITY_EST_MONTHLY  = 300

# ---- Score weights (normalised, so they need not sum to 1.0) --------------
WEIGHT_PRICE_SQFT    = 0.30
WEIGHT_TOTAL_MONTHLY = 0.40
WEIGHT_COMMUTE_MINS  = 0.20
WEIGHT_LIRR          = 0.10

LIRR_PENALTY_MINS = 30   # assumed when a listing names no station
TOP_N             = 20   # listings in the text report
