#!/usr/bin/env python3
"""
============================================================
 Commute Cost Ranker
 Step 1b: Process Raw JSON -> Clean CSV
============================================================
 Splits listings into two budget zones by town, drops the
 ones that miss the requirements, and flattens the rest into
 a CSV the scoring pipeline can read.

 Every row gets a "zone" column (CLOSE / FAR) so step2 can
 compare the two side by side.

 Zones, budgets, towns and minimums all come from config.py.
 See config_example.py.
============================================================
"""

import json
import math
import csv
import os
from collections import Counter

import settings
from settings import (CLOSE_TOWNS, CLOSE_BUDGET, FAR_TOWNS, FAR_BUDGET,
                      MIN_BEDS, MIN_BATHS, OFFICE_LAT, OFFICE_LON)

INPUT_FILE   = settings.RAW_FILE
OUTPUT_FILE  = settings.CLEAN_FILE

# ============================================================
# HELPERS
# ============================================================

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2-lat1)/2)**2
         + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def get_score(scores, keyword):
    for s in (scores or []):
        if s and keyword.lower() in s.get("type", "").lower():
            return s.get("score", "")
    return ""

def get_lirr(transport):
    for t in (transport or []):
        if "commuter rail" in t.get("type", "").lower():
            return f"{t.get('name', '')} ({t.get('distance', '')})"
    return "N/A"

# ============================================================
# FILTER
# ============================================================

def pre_filter(items):
    close, far = [], []
    skipped = {"no_price": 0, "no_coords": 0, "beds_baths": 0,
               "wrong_town": 0, "over_budget": 0}
    unlisted_towns   = Counter()   # scraped, but in no town list
    over_budget_towns = Counter()  # right town, priced out

    for item in items:
        price = item.get("price")
        if not price or price <= 0:
            skipped["no_price"] += 1; continue

        beds  = item.get("beds")  or 0
        baths = item.get("baths") or 0
        if beds < MIN_BEDS or baths < MIN_BATHS:
            skipped["beds_baths"] += 1; continue

        coord = item.get("coordinate", {})
        lat   = coord.get("latitude")
        lon   = coord.get("longitude")
        if not lat or not lon:
            skipped["no_coords"] += 1; continue

        city = (item.get("city") or "").strip().lower()

        if city in CLOSE_TOWNS:
            if price > CLOSE_BUDGET:
                skipped["over_budget"] += 1
                over_budget_towns[item.get("city") or "?"] += 1
                continue
            item["_zone"]            = "CLOSE"
            item["_dist_to_office"]  = round(haversine_miles(lat, lon, OFFICE_LAT, OFFICE_LON), 2)
            close.append(item)

        elif city in FAR_TOWNS:
            if price > FAR_BUDGET:
                skipped["over_budget"] += 1
                over_budget_towns[item.get("city") or "?"] += 1
                continue
            item["_zone"]            = "FAR"
            item["_dist_to_office"]  = round(haversine_miles(lat, lon, OFFICE_LAT, OFFICE_LON), 2)
            far.append(item)

        else:
            skipped["wrong_town"] += 1
            unlisted_towns[item.get("city") or "?"] += 1

    close_names = ", ".join(sorted(CLOSE_TOWNS))
    far_names   = ", ".join(sorted(FAR_TOWNS))

    print("Pre-filter summary:")
    print(f"  CLOSE ({close_names}) <= ${CLOSE_BUDGET:,}: {len(close)}")
    print(f"  FAR   ({far_names})  <= ${FAR_BUDGET:,}: {len(far)}")
    for reason, count in skipped.items():
        if count:
            print(f"  Skipped ({reason}): {count}")

    # These two breakdowns tell you where the lost listings went, so you can
    # decide whether to widen a town list or raise a budget.
    if unlisted_towns:
        detail = ", ".join(f"{town} {n}" for town, n in unlisted_towns.most_common())
        print(f"  -> scraped but in no town list: {detail}")
    if over_budget_towns:
        detail = ", ".join(f"{town} {n}" for town, n in over_budget_towns.most_common())
        print(f"  -> priced out of their zone budget: {detail}")

    print()
    return close + far

# ============================================================
# NORMALIZE
# ============================================================

def normalize(items):
    rows = []
    for item in items:
        amenities = item.get("amenities", {})
        if not isinstance(amenities, dict): amenities = {}

        coord     = item.get("coordinate", {})
        scores    = [s for s in (item.get("scores") or []) if s and s.get("type")]
        transport = item.get("transportation") or []

        annual_tax = (item.get("recentPropertyTax")
                      or amenities.get("Tax Annual Amount") or "")
        try:
            annual_tax = float(str(annual_tax).replace(",", "").strip())
        except (ValueError, TypeError):
            annual_tax = ""

        rows.append({
            # Identity
            "url":           item.get("url", ""),
            "address":       item.get("propertyFullAddress", ""),
            "city":          item.get("city", ""),
            "state":         item.get("state", ""),
            "zip":           item.get("postalCode", ""),
            "zone":          item.get("_zone", ""),          # CLOSE or FAR

            # Property
            "price":         item.get("price", 0),
            "beds":          item.get("beds", 0),
            "baths":         item.get("baths", 0),
            "sqft":          item.get("sqft", 0) or 0,
            "lot_sqft":      amenities.get("Lot Size Sq Ft", ""),
            "year_built":    item.get("yearBuilt", ""),
            "style":         amenities.get("Architectural Style", ""),
            "list_date":     item.get("listDate", ""),
            "mls_number":    item.get("mlsNumber", ""),

            # Financials
            "annual_tax":    annual_tax,
            "hoa_monthly":   amenities.get("Association Fee", ""),
            "garage":        amenities.get("Garage", "") or amenities.get("Garage Yes", ""),
            "garage_spaces": amenities.get("Garage Spaces", ""),
            "heating":       amenities.get("Heating", ""),
            "cooling":       amenities.get("Cooling", ""),
            "basement":      amenities.get("Basement", ""),
            "pool":          amenities.get("Pool Private", "") or amenities.get("Pool Private Yes", ""),

            # Location
            "lat":              coord.get("latitude", ""),
            "lng":              coord.get("longitude", ""),
            "neighborhood":     item.get("neighborhood", ""),
            "dist_to_office_mi":item.get("_dist_to_office", ""),

            # Transit
            "lirr_nearest":  get_lirr(transport),

            # Scores
            "walk_score":    get_score(scores, "Walk Score"),
            "transit_score": get_score(scores, "Transit Score"),
            "crime_score":   get_score(scores, "Crime Score"),
            "flood_factor":  get_score(scores, "Flood Factor"),

            # Agent
            "agent_name":    item.get("agentName", ""),
            "agency":        item.get("agencyName", ""),
            "agent_phone":   item.get("agentPhone", ""),

            # Placeholders filled by step2_scoring_pipeline.py
            "drive_time_to_office_mins": "",
            "drive_miles_to_office":     "",
            "lirr_station_name":         "",
            "lirr_drive_mins":           "",
            "daily_gas_cost":            "",
            "monthly_gas_cost":          "",
            "annual_gas_cost":           "",
            "monthly_mortgage":          "",
            "monthly_tax":               "",
            "monthly_hoa":               "",
            "monthly_total_cost":        "",
            "price_per_sqft":            "",
            "value_score":               "",
        })

    print(f"Normalized {len(rows)} listings.")
    return rows

# ============================================================
# SAVE
# ============================================================

def save_csv(rows, path):
    if not rows:
        print("No rows to save — check town names and budgets."); return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"Saved {len(rows)} listings -> {path}")

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Step 1b: raw_listings.json -> listings_clean.csv")
    print("=" * 60)
    print()

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found in current directory.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    print(f"Loaded {len(raw)} raw listings")
    print()

    filtered = pre_filter(raw)
    clean    = normalize(filtered)
    save_csv(clean, OUTPUT_FILE)

    print()
    print("=" * 60)
    print(f"  Done! {len(clean)} listings -> output/listings_clean.csv")
    print("  Next: run step2_scoring_pipeline.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
