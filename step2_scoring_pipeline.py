#!/usr/bin/env python3
"""
Commute Cost Ranker
Step 2: Scoring Pipeline

New columns added:
  drive_time_to_office_mins  - Google Maps drive time to office
  drive_miles_to_office      - Road miles to office
  daily_gas_cost             - Gas cost for one round-trip day
  monthly_gas_cost           - Gas cost per month (workdays only)
  annual_gas_cost            - Gas cost per year
  lirr_station_name          - Nearest LIRR station name
  lirr_drive_mins            - Drive time to nearest LIRR station
                               (Google Maps if key set, else parsed from listing)

SETUP:  pip install googlemaps pandas
USAGE:  set GOOGLE_MAPS_API_KEY env var, then run this script.

All tuning - workplace, commute pattern, financial assumptions and
score weights - lives in config.py. See config_example.py.
"""

import os
import re
import time
import pandas as pd
from datetime import datetime

import settings
from settings import (OFFICE_COORDS, COMMUTE_DAYS_PER_WEEK, WORK_WEEKS_PER_YEAR,
                      MORTGAGE_RATE, MORTGAGE_TERM_YEARS, DOWN_PAYMENT_PCT,
                      GAS_PRICE_PER_GALLON, CAR_MPG, UTILITY_EST_MONTHLY,
                      WEIGHT_PRICE_SQFT, WEIGHT_TOTAL_MONTHLY,
                      WEIGHT_COMMUTE_MINS, WEIGHT_LIRR,
                      LIRR_PENALTY_MINS, TOP_N, STATION_GEOCODE_REGION)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_KEY_HERE")

INPUT_FILE  = settings.CLEAN_FILE
OUTPUT_FILE = settings.SCORED_FILE
REPORT_FILE = settings.REPORT_FILE

# ================================================================
# HELPERS
# ================================================================

def monthly_payment(price, rate=None, term=None, down_pct=None):
    rate     = rate     or MORTGAGE_RATE
    term     = term     or MORTGAGE_TERM_YEARS
    down_pct = down_pct or DOWN_PAYMENT_PCT
    principal = price * (1 - down_pct)
    r = rate / 12
    n = term * 12
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)


def gas_cost_per_mile():
    return GAS_PRICE_PER_GALLON / CAR_MPG


def parse_lirr_station(lirr_str):
    """Extract station name from lirr_nearest field.
    "Babylon Station (4 min drive)" -> "Babylon Station"
    """
    if not lirr_str or str(lirr_str).strip() in ("N/A", "", "nan"):
        return ""
    match = re.match(r"^(.+?)\s*\(", str(lirr_str))
    return match.group(1).strip() if match else str(lirr_str)


def parse_lirr_mins_from_text(lirr_str):
    """Parse drive/walk minutes from lirr_nearest field as fallback.
    "Babylon Station (4 min drive)" -> 4
    """
    if not lirr_str or str(lirr_str).strip() in ("N/A", "", "nan"):
        return LIRR_PENALTY_MINS
    match = re.search(r"(\d+)\s*min", str(lirr_str))
    return int(match.group(1)) if match else LIRR_PENALTY_MINS


# ================================================================
# GOOGLE MAPS LOOKUPS
# ================================================================

def _has_gmaps():
    """Return gmaps client if API key is configured, else None."""
    if GOOGLE_MAPS_API_KEY == "YOUR_KEY_HERE":
        return None
    try:
        import googlemaps
        return googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    except ImportError:
        return None


def _batch_distance_matrix(gmaps, origins, destinations, label=""):
    """
    Run Distance Matrix in batches of 25.
    Returns list of (duration_mins, distance_miles) per origin.
    Uses duration_in_traffic when available, falls back to duration.
    """
    BATCH   = 25
    results = []
    total   = len(origins)

    for i in range(0, total, BATCH):
        o_chunk = origins[i:i+BATCH]
        response = gmaps.distance_matrix(
            origins=o_chunk,
            destinations=destinations,
            mode="driving",
            departure_time="now",
            units="imperial"
        )
        for row_data in response["rows"]:
            elem = row_data["elements"][0]
            if elem["status"] == "OK":
                dur = elem.get("duration_in_traffic", elem["duration"])["value"]
                dst = elem["distance"]["value"]
                results.append((round(dur / 60), round(dst / 1609.34, 2)))
            else:
                results.append((0, 0))
        if label:
            print(f"  {label}: {min(i+BATCH, total)}/{total}")
        time.sleep(0.1)

    return results


def fetch_office_commute(df):
    """
    Adds: drive_time_to_office_mins, drive_miles_to_office
    Uses Google Maps if key set, else haversine x 2.5 min/mi estimate.
    """
    gmaps = _has_gmaps()

    if gmaps is None:
        print("  No API key — estimating office commute via straight-line distance.")
        df["drive_time_to_office_mins"] = df["dist_to_office_mi"].apply(
            lambda x: round(float(x) * 2.5)
            if str(x).replace(".", "").isdigit() else 0
        )
        df["drive_miles_to_office"] = pd.to_numeric(
            df["dist_to_office_mi"], errors="coerce"
        ).round(2)
        return df

    print(f"[1/2] Fetching office commute times ({len(df)} listings)...")
    origins = list(zip(df["lat"], df["lng"]))
    res     = _batch_distance_matrix(gmaps, origins, [OFFICE_COORDS], "Office")

    df["drive_time_to_office_mins"] = [r[0] for r in res]
    df["drive_miles_to_office"]     = [r[1] for r in res]
    return df


def fetch_lirr_commute(df):
    """
    Adds: lirr_station_name, lirr_drive_mins
    Attempts Google Maps lookup from home -> nearest LIRR station.
    Falls back to minutes parsed from the listing text.
    """
    # Always parse station name and fallback mins
    df["lirr_station_name"] = df["lirr_nearest"].apply(parse_lirr_station)
    df["lirr_drive_mins"]   = df["lirr_nearest"].apply(parse_lirr_mins_from_text)

    gmaps = _has_gmaps()
    if gmaps is None:
        print("  No API key — using LIRR times parsed from listing text.")
        return df

    # Build per-row destination: station name + the configured region.
    # The region matters - a bare station name geocodes to the wrong state
    # often enough to produce plausible but wrong drive times.
    # Rows with no station keep the parsed fallback
    has_station = df["lirr_station_name"] != ""
    if not has_station.any():
        print("  No LIRR stations found in data — skipping Google Maps LIRR lookup.")
        return df

    sub      = df[has_station].copy()
    origins  = list(zip(sub["lat"], sub["lng"]))
    dests    = [f"{name}, {STATION_GEOCODE_REGION}" for name in sub["lirr_station_name"]]

    print(f"[2/2] Fetching LIRR drive times ({len(sub)} listings)...")
    BATCH = 25
    lirr_mins_real = []

    for i in range(0, len(sub), BATCH):
        o_chunk = origins[i:i+BATCH]
        d_chunk = dests[i:i+BATCH]

        # Each origin goes to its own unique destination, so we call one at a time
        # (Distance Matrix: 1 origin x 1 destination per row)
        for origin, dest in zip(o_chunk, d_chunk):
            response = gmaps.distance_matrix(
                origins=[origin],
                destinations=[dest],
                mode="driving",
                departure_time="now",
                units="imperial"
            )
            elem = response["rows"][0]["elements"][0]
            if elem["status"] == "OK":
                dur = elem.get("duration_in_traffic", elem["duration"])["value"]
                lirr_mins_real.append(round(dur / 60))
            else:
                lirr_mins_real.append(None)
        print(f"  LIRR: {min(i+BATCH, len(sub))}/{len(sub)}")
        time.sleep(0.1)

    # Write back only to rows that had a station
    sub_index = sub.index
    for idx, mins in zip(sub_index, lirr_mins_real):
        if mins is not None:
            df.at[idx, "lirr_drive_mins"] = mins

    return df


# ================================================================
# COST CALCULATIONS
# ================================================================

def calculate_costs(df):
    # Monthly mortgage
    df["monthly_mortgage"] = df["price"].apply(
        lambda p: round(monthly_payment(float(p))) if p else 0
    )

    # Monthly tax
    def parse_tax(t):
        try:
            return round(float(str(t).replace(",", "").strip()) / 12)
        except (ValueError, TypeError):
            return 0
    df["monthly_tax"] = df["annual_tax"].apply(parse_tax)

    # Monthly HOA
    df["monthly_hoa"] = df["hoa_monthly"].apply(
        lambda h: round(float(h)) if str(h).replace(".", "").isdigit() else 0
    )

    # Gas cost — three granularities
    # Uses drive_miles_to_office (road miles from Google Maps or haversine)
    cost_per_mile = gas_cost_per_mile()

    def get_miles(row):
        try:
            return float(row.get("drive_miles_to_office") or
                         row.get("dist_to_office_mi") or 0)
        except (ValueError, TypeError):
            return 0

    df["daily_gas_cost"] = df.apply(
        lambda r: round(get_miles(r) * 2 * cost_per_mile, 2),   # round trip
        axis=1
    )
    df["annual_gas_cost"] = df.apply(
        lambda r: round(get_miles(r) * 2 * COMMUTE_DAYS_PER_WEEK *
                        WORK_WEEKS_PER_YEAR * cost_per_mile),
        axis=1
    )
    # Derived from the annual figure so the two always agree
    # (monthly * 12 == annual, both on WORK_WEEKS_PER_YEAR).
    df["monthly_gas_cost"] = (df["annual_gas_cost"] / 12).round().astype(int)

    # All-in monthly cost
    df["monthly_total_cost"] = (
        df["monthly_mortgage"]
        + df["monthly_tax"]
        + df["monthly_hoa"]
        + df["monthly_gas_cost"]
        + UTILITY_EST_MONTHLY
    )

    # Price per sqft - NaN (not 0) when sqft is unknown, so score_listings
    # treats it as "no data / worst case" rather than "free square footage".
    def price_per_sqft(row):
        try:
            sqft = float(row.get("sqft") or 0)
        except (ValueError, TypeError):
            return float("nan")
        if sqft <= 0:
            return float("nan")
        return round(float(row["price"]) / sqft)

    df["price_per_sqft"] = df.apply(price_per_sqft, axis=1)

    return df


# ================================================================
# VALUE SCORE
# ================================================================

def score_listings(df):
    """Composite value score 0-100 (higher = better).
    Factors: price/sqft, total monthly cost, drive commute, LIRR proximity.
    """
    def norm_low(s):
        """Normalize to 0-100 where LOWER input = HIGHER score.

        Missing / unparseable values are filled with the worst (highest)
        observed value, so a listing with no data scores 0 on that factor
        instead of accidentally scoring 100.
        """
        s = pd.to_numeric(s, errors="coerce")
        worst = s.max()
        s = s.fillna(worst)
        lo, hi = s.min(), s.max()
        if pd.isna(lo) or hi == lo:
            # No usable spread - don't let one factor swing the ranking.
            return pd.Series(50.0, index=s.index)
        return 100 * (1 - (s - lo) / (hi - lo))

    df["_n_price_sqft"] = norm_low(df["price_per_sqft"])
    df["_n_monthly"]    = norm_low(df["monthly_total_cost"])
    df["_n_commute"]    = norm_low(df["drive_time_to_office_mins"])
    df["_n_lirr"]       = norm_low(df["lirr_drive_mins"])

    df["value_score"] = (
        WEIGHT_PRICE_SQFT    * df["_n_price_sqft"]
        + WEIGHT_TOTAL_MONTHLY * df["_n_monthly"]
        + WEIGHT_COMMUTE_MINS  * df["_n_commute"]
        + WEIGHT_LIRR          * df["_n_lirr"]
    ).round(1)

    df.drop(columns=[c for c in df.columns if c.startswith("_n_")], inplace=True)
    df.sort_values("value_score", ascending=False, inplace=True)
    return df


# ================================================================
# REPORT
# ================================================================

def generate_report(df, output_path):
    top  = df.head(TOP_N)
    SEP  = "-" * 70
    DSEP = "=" * 70

    missing_sqft = int(df["price_per_sqft"].isna().sum())

    lines = [
        DSEP,
        f"  TOP {len(top)} BEST VALUE HOMES -- LONG ISLAND NY"
            + (f"  (all {len(df)} that passed the filters)" if len(top) == len(df) else ""),
        f"  Generated     : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"  Mortgage      : {MORTGAGE_RATE*100:.2f}% fixed, {DOWN_PAYMENT_PCT*100:.0f}% down",
        f"  Gas           : ${GAS_PRICE_PER_GALLON}/gal | {CAR_MPG} mpg",
        f"  Commute days  : {COMMUTE_DAYS_PER_WEEK}d/wk | {WORK_WEEKS_PER_YEAR} wks/yr",
        f"  Score weights : price/sqft {WEIGHT_PRICE_SQFT*100:.0f}%  "
            f"monthly {WEIGHT_TOTAL_MONTHLY*100:.0f}%  "
            f"commute {WEIGHT_COMMUTE_MINS*100:.0f}%  "
            f"LIRR {WEIGHT_LIRR*100:.0f}%",
        DSEP,
        f"  NOTE: value_score is RELATIVE to these {len(df)} listings only -",
        "        it is a ranking within this batch, not an absolute rating.",
    ]
    if missing_sqft:
        lines.append(
            f"  NOTE: {missing_sqft} listing(s) have no sqft -> scored 0 on price/sqft."
        )
    lines.append(DSEP)

    for rank, (_, row) in enumerate(top.iterrows(), 1):
        annual_tax = float(row.get("annual_tax") or 0)
        sqft_str   = str(int(row["sqft"])) if row["sqft"] else "N/A"
        pps        = row.get("price_per_sqft")
        pps_str    = "N/A (no sqft)" if pd.isna(pps) else f"${pps:,.0f}/sqft"
        principal  = row["price"] * (1 - DOWN_PAYMENT_PCT)
        off_mi     = row.get("drive_miles_to_office", row.get("dist_to_office_mi", "?"))

        lines += [
            "",
            SEP,
            f"  #{rank:<3}  {row['address']}",
            f"       VALUE SCORE    : {row['value_score']}  |  "
                f"${row['price']:>9,.0f}  |  {row['beds']}bd/{row['baths']}ba  |  "
                f"{sqft_str} sqft  |  {pps_str}",
            f"       Year Built     : {row.get('year_built', 'N/A')}  |  "
                f"Style: {row.get('style', 'N/A')}  |  Lot: {row.get('lot_sqft', 'N/A')} sqft",
            "       MONTHLY BREAKDOWN:",
            f"         Mortgage     : ${row['monthly_mortgage']:>7,.0f}  "
                f"(${principal:,.0f} @ {MORTGAGE_RATE*100:.2f}%)",
            f"         Tax          : ${row['monthly_tax']:>7,.0f}  (annual ${annual_tax:,.0f})",
            f"         HOA          : ${row['monthly_hoa']:>7,.0f}",
            f"         Gas (monthly): ${row['monthly_gas_cost']:>7,.0f}  "
                f"(${row['daily_gas_cost']:.2f}/day | ${row['annual_gas_cost']:,.0f}/yr)",
            f"         Utilities    : ${UTILITY_EST_MONTHLY:>7,.0f}  (estimate)",
            "         " + "-" * 38,
            f"         TOTAL        : ${row['monthly_total_cost']:>7,.0f} / month",
            "       COMMUTE TO OFFICE:",
            f"         Drive time   : {row.get('drive_time_to_office_mins', '?')} min",
            f"         Drive miles  : {off_mi} mi",
            f"         Annual gas $ : ${row['annual_gas_cost']:,.0f}",
            "       NEAREST LIRR:",
            f"         Station      : {row.get('lirr_station_name', 'N/A')}",
            f"         Drive time   : {row.get('lirr_drive_mins', '?')} min",
            "       HOME DETAILS:",
            f"         Heating      : {row.get('heating', 'N/A')}  |  "
                f"Cooling: {row.get('cooling', 'N/A')}  |  "
                f"Garage: {row.get('garage_spaces', 'N/A')} car",
            f"         Basement     : {row.get('basement', 'N/A')}  |  Pool: {row.get('pool', 'N/A')}",
            f"         Flood factor : {row.get('flood_factor', 'N/A')}  |  "
                f"Crime: {row.get('crime_score', 'N/A')}  |  "
                f"Walk Score: {row.get('walk_score', 'N/A')}",
            f"       AGENT          : {row.get('agent_name', 'N/A')} -- "
                f"{row.get('agent_phone', 'N/A')} ({row.get('agency', 'N/A')})",
            f"       URL            : {row.get('url', '')}",
        ]

    lines += ["", DSEP, f"  Full data -> {OUTPUT_FILE}", DSEP]
    report = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\nReport saved -> {output_path}")


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 60)
    print("  Step 2: Scoring Pipeline")
    print("=" * 60)
    settings.banner()
    print()

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found.")
        print("  Run step1b_process_json.py first.")
        return

    df = pd.read_csv(INPUT_FILE, dtype=str)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["beds"]  = pd.to_numeric(df["beds"],  errors="coerce").fillna(0)
    df["baths"] = pd.to_numeric(df["baths"], errors="coerce").fillna(0)
    df["sqft"]  = pd.to_numeric(df["sqft"],  errors="coerce").fillna(0)

    print(f"Loaded {len(df)} clean listings from {INPUT_FILE}")
    print()

    # Two separate Google Maps calls:
    # 1. Each home -> office
    # 2. Each home -> its nearest LIRR station
    df = fetch_office_commute(df)
    df = fetch_lirr_commute(df)
    df = calculate_costs(df)
    df = score_listings(df)

    os.makedirs("output", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved scored listings -> {OUTPUT_FILE}")
    print()

    generate_report(df, REPORT_FILE)


if __name__ == "__main__":
    main()
