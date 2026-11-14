"""
============================================================
 Homes.com Scraper - Long Island NY Home Value Analysis
 Step 1 of 3: Data Collection ONLY
============================================================
 This script does one job: pull raw listings from Homes.com
 via Apify and save them to output/raw_listings.json.

 All filtering / budget / town logic lives in ONE place:
   step1b_process_json.py   (filter + normalize -> clean CSV)
   step2_scoring_pipeline.py (commute, costs, value score)

 Scraping is the slow, paid part. Keeping it separate means
 you can re-tune budgets and towns and re-run step1b/step2
 as many times as you like without re-scraping.

 SETUP:
   pip install apify-client
   Set your token (PowerShell):
     $env:APIFY_API_TOKEN = "apify_api_..."
   Or permanently:
     setx APIFY_API_TOKEN "apify_api_..."

 USAGE:
   python step1_scraper.py
   python step1b_process_json.py
   python step2_scoring_pipeline.py
============================================================
"""
import os
import json
from datetime import datetime

from apify_client import ApifyClient

import settings

# ============================================================
# CONFIGURATION
# ============================================================

# Never hardcode credentials here - read them from the environment.
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

# Apify actor
ACTOR_ID = "epctex/homes-com-scraper"

# Search URLs, page depth and item cap all come from config.py.
# See config_example.py.
START_URLS = settings.START_URLS
END_PAGE   = settings.END_PAGE
MAX_ITEMS  = settings.MAX_ITEMS

RAW_FILE   = settings.RAW_FILE


# ============================================================
# SCRAPE
# ============================================================

def run_apify_scraper(token: str) -> list[dict]:
    """Call the Apify actor and return the raw dataset items."""
    client = ApifyClient(token)

    actor_input = {
        "startUrls": START_URLS,
        "endPage":   END_PAGE,
        "maxItems":  MAX_ITEMS,
        "proxy": {
            "useApifyProxy": True,
        },
    }

    print(f"[{datetime.now():%H:%M:%S}] Starting Apify actor: {ACTOR_ID}")
    print(f"  {len(START_URLS)} search URLs x {END_PAGE} pages, max {MAX_ITEMS} items...")

    run = client.actor(ACTOR_ID).call(run_input=actor_input)

    items = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]

    print(f"[{datetime.now():%H:%M:%S}] Scrape complete - {len(items)} raw listings retrieved.")
    return items


def save_raw(items: list[dict], path: str = RAW_FILE) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"  Saved raw JSON -> {path}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  STEP 1: Listing Scraper")
    print("=" * 60)
    settings.banner()
    print()

    if not APIFY_API_TOKEN:
        print("ERROR: APIFY_API_TOKEN is not set in your environment.")
        print("  PowerShell:  $env:APIFY_API_TOKEN = \"apify_api_...\"")
        print("  Persistent:  setx APIFY_API_TOKEN \"apify_api_...\"")
        print("  Get a token: https://console.apify.com -> Settings -> Integrations")
        return

    # Don't silently destroy a good scrape if this run fails.
    if os.path.exists(RAW_FILE):
        backup = RAW_FILE.replace(".json", f".{datetime.now():%Y%m%d_%H%M%S}.bak.json")
        os.replace(RAW_FILE, backup)
        print(f"  Existing raw data moved aside -> {backup}")

    raw_items = run_apify_scraper(APIFY_API_TOKEN)
    save_raw(raw_items)

    print()
    print("=" * 60)
    print(f"  Done! {len(raw_items)} raw listings -> {RAW_FILE}")
    print("  Next: python step1b_process_json.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
