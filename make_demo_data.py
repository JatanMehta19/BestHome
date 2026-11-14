#!/usr/bin/env python3
"""
============================================================
 Commute Cost Ranker - synthetic demo dataset generator
============================================================
 Builds site/demo_listings.json for the public demo.

 WHY SYNTHETIC:
   The private pipeline (step1/step1b/step2) runs against
   live scraped listings. That data is NOT suitable to
   publish:
     - it is CoStar/Homes.com content, which their terms and
       litigation history put off limits for redistribution
     - it carries real listing agents' names and phone
       numbers (third-party personal data)
     - it is tied to one person's actual house search

   So the demo ships invented listings whose DISTRIBUTIONS
   are calibrated to the real scrape: the price band, median
   sqft, and effective property tax rates (1.3-1.7% of price
   on Long Island). Street names, house numbers and
   coordinates are generated. No agent data at all. The
   scoring engine the demo runs is the real one.

   The towns below are also deliberately NOT the ones the
   private pipeline searches. A demo built on someone's own
   shortlist would hand a reader their search area, and the
   near-zone towns would triangulate their workplace.

 Deterministic: fixed seed, so the demo never shifts.
============================================================
"""
import json
import math
import os
import random

SEED = 20260413
TARGET_COUNT = 72
OUT_PATH = os.path.join("site", "demo_listings.json")

# ---- Towns: real public geography (centroid, spread, LIRR station) ----
# A broad spread across Nassau and Suffolk, north shore and south, so the
# dataset reads as a sample of Long Island rather than as anyone's shortlist.
#
# The per-town price and sqft figures are plausible values drawn from the
# BAND measured in the private scrape (medians roughly $580-790K, effective
# property tax 1.3-1.7% of price). They are not per-town measurements.
TOWNS = [
    # Nassau
    ("Mineola",         40.7493, -73.6409, 0.012, 775_000, 1_600, 0.0142, "Mineola Station",        "Main Line"),
    ("Westbury",        40.7557, -73.5876, 0.014, 735_000, 1_700, 0.0155, "Westbury Station",       "Main Line"),
    ("Franklin Square", 40.7001, -73.6779, 0.012, 725_000, 1_500, 0.0148, "Floral Park Station",    "Main Line"),
    ("Valley Stream",   40.6643, -73.7085, 0.015, 699_000, 1_550, 0.0162, "Valley Stream Station",  "Babylon"),
    ("Massapequa",      40.6807, -73.4746, 0.016, 749_000, 1_800, 0.0158, "Massapequa Station",     "Babylon"),
    ("Seaford",         40.6665, -73.4885, 0.011, 719_000, 1_650, 0.0160, "Seaford Station",        "Babylon"),
    # Suffolk - north shore
    ("Huntington",      40.8681, -73.4257, 0.019, 789_000, 2_000, 0.0148, "Huntington Station",     "Port Jefferson"),
    ("Kings Park",      40.8873, -73.2454, 0.013, 679_000, 1_850, 0.0152, "Kings Park Station",     "Port Jefferson"),
    ("Smithtown",       40.8559, -73.2004, 0.017, 749_000, 2_100, 0.0155, "Smithtown Station",      "Port Jefferson"),
    ("Stony Brook",     40.9257, -73.1409, 0.014, 719_000, 2_200, 0.0163, "Stony Brook Station",    "Port Jefferson"),
    ("Port Jefferson",  40.9465, -73.0693, 0.015, 639_000, 1_900, 0.0157, "Port Jefferson Station", "Port Jefferson"),
    # Suffolk - south shore
    ("Babylon",         40.6959, -73.3254, 0.013, 699_000, 1_700, 0.0144, "Babylon Station",        "Babylon"),
    ("Bay Shore",       40.7254, -73.2454, 0.016, 609_000, 1_650, 0.0151, "Bay Shore Station",      "Montauk"),
    ("Islip",           40.7301, -73.2104, 0.012, 649_000, 1_750, 0.0146, "Islip Station",          "Montauk"),
    ("Sayville",        40.7362, -73.0821, 0.014, 669_000, 1_800, 0.0149, "Sayville Station",       "Montauk"),
    ("Patchogue",       40.7657, -73.0151, 0.018, 579_000, 1_500, 0.0138, "Patchogue Station",      "Montauk"),
]

# Invented street names - deliberately NOT the real ones from the scrape.
STREETS = [
    "Alder Ct", "Birchwood Dr", "Cedar Ridge Rd", "Dogwood Ln", "Elmhurst Ave",
    "Fernway Dr", "Garland St", "Hawthorn Ct", "Ivy Hill Rd", "Juniper Ln",
    "Kingsbury Ave", "Larkspur Dr", "Mulberry Ct", "Nightingale Rd", "Orchard Hill Dr",
    "Primrose Ln", "Quarry Rd", "Rosewood Ave", "Sycamore Ct", "Thistle Dr",
    "Underhill Rd", "Vineyard Ln", "Willowbrook Dr", "Yardley Ct", "Ashgrove Ln",
    "Bramble Ct", "Clearspring Rd", "Deerfield Ave", "Eastgate Dr", "Foxglove Ln",
]

STYLES = ["Colonial", "Ranch", "Cape Cod", "Split Level", "Hi Ranch", "Exp Cape", "Saltbox", "Contemporary"]
HEATING = ["Natural Gas, Forced Air", "Oil, Baseboard", "Natural Gas, Baseboard", "Electric, Heat Pump"]
BASEMENTS = ["Full, Unfinished", "Full, Finished", "Partial", "Crawl Space", "None"]


def jitter(rng, center, spread):
    """Coordinate inside a town, clustered toward the middle."""
    return center + rng.gauss(0, spread / 2.2)


def pick_price(rng, median):
    """Right-skewed around the town median, like a real listing set."""
    p = median * math.exp(rng.gauss(0, 0.19))
    return int(round(max(379_000, min(1_150_000, p)) / 1000) * 1000) - 1


def build():
    rng = random.Random(SEED)
    rows = []
    used = set()

    # Rough inventory weighting, so the sample is not perfectly uniform.
    weights = [2, 2, 2, 3, 3, 2, 3, 2, 2, 2, 2, 2, 3, 2, 2, 3]
    assert len(weights) == len(TOWNS), "one weight per town"

    while len(rows) < TARGET_COUNT:
        town = rng.choices(TOWNS, weights=weights, k=1)[0]
        name, lat, lng, spread, med_price, med_sqft, tax_rate, station, branch = town

        number = rng.choice([rng.randint(1, 99), rng.randint(100, 399), rng.randint(400, 1299)])
        street = rng.choice(STREETS)
        address = str(number) + " " + street
        key = (address, name)
        if key in used:
            continue
        used.add(key)

        price = pick_price(rng, med_price)

        # ~6% of listings genuinely have no sqft. The demo needs these, because
        # handling missing data honestly is part of what the scoring shows.
        has_sqft = rng.random() > 0.06
        sqft = int(round(med_sqft * math.exp(rng.gauss(0, 0.22)) / 10) * 10) if has_sqft else 0

        beds = rng.choices([2, 3, 4, 5], weights=[1, 5, 4, 1])[0]
        baths = rng.choices([1, 2, 3, 4], weights=[2, 6, 2, 1])[0]

        # Effective rate on the town assessment, with real-world noise.
        annual_tax = int(round(price * tax_rate * rng.uniform(0.84, 1.18) / 10) * 10)

        hoa = 0 if rng.random() > 0.14 else rng.choice([145, 195, 240, 310, 385])

        year_built = rng.choices(
            [rng.randint(1925, 1949), rng.randint(1950, 1979),
             rng.randint(1980, 2009), rng.randint(2010, 2024)],
            weights=[2, 5, 2, 1])[0]

        rows.append({
            "id":              "demo-" + str(len(rows) + 1).zfill(3),
            "address":         address,
            "city":            name,
            "state":           "NY",
            "full_address":    address + ", " + name + ", NY",
            "price":           price,
            "beds":            beds,
            "baths":           baths,
            "sqft":            sqft,
            "lot_sqft":        int(round(rng.uniform(4_000, 24_000) / 100) * 100),
            "year_built":      year_built,
            "style":           rng.choice(STYLES),
            "annual_tax":      annual_tax,
            "hoa_monthly":     hoa,
            "heating":         rng.choice(HEATING),
            "cooling":         rng.choice(["Central Air", "Central Air", "Wall Unit", "None"]),
            "basement":        rng.choice(BASEMENTS),
            "garage_spaces":   rng.choices([0, 1, 2, 3], weights=[2, 3, 4, 1])[0],
            "lat":             round(jitter(rng, lat, spread), 5),
            "lng":             round(jitter(rng, lng, spread), 5),
            "lirr_station":    station,
            "lirr_branch":     branch,
            "lirr_drive_mins": rng.choices([2, 3, 4, 5, 6, 8, 10, 13, 17, 22, 28],
                                           weights=[2, 3, 4, 5, 5, 4, 3, 3, 2, 1, 1])[0],
            "walk_score":      rng.randint(12, 72),
            "transit_score":   rng.randint(15, 48),
            "crime_score":     rng.randint(1, 5),
            "flood_factor":    rng.choices([1, 2, 3, 4], weights=[7, 2, 1, 1])[0],
            "days_on_market":  rng.choices([rng.randint(1, 14), rng.randint(15, 60), rng.randint(61, 210)],
                                           weights=[3, 4, 2])[0],
        })

    rows.sort(key=lambda r: (r["city"], r["address"]))
    return rows


def main():
    rows = build()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    payload = {
        "synthetic": True,
        "note": ("Invented listings. Prices, square footage and property-tax rates are "
                 "calibrated to real Long Island market distributions, but no listing, "
                 "address or agent here is real."),
        "generated_by": "make_demo_data.py",
        "seed": SEED,
        "count": len(rows),
        "listings": rows,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    from collections import Counter
    import statistics as stx
    print("Wrote " + str(len(rows)) + " synthetic listings -> " + OUT_PATH)
    print("  median price  $" + format(stx.median(r["price"] for r in rows), ",.0f"))
    print("  no-sqft rows  " + str(sum(1 for r in rows if not r["sqft"])))
    print("  towns         " + str(dict(Counter(r["city"] for r in rows))))


if __name__ == "__main__":
    main()
