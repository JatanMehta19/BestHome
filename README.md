# Commute Cost Ranker

**Is the cheaper house actually cheaper?**

A house 25 miles out costs less to buy and more to reach. Listing sites answer
"what's the payment?" and commute tools answer "how long is the drive?" — neither
answers the question you're actually asking, which is what the whole arrangement
costs per month once both are counted.

This ranks listings on all-in monthly cost — mortgage, property tax, HOA,
utilities and the fuel burned commuting — and lets you set **a different budget
ceiling for near and far**. That last part is the idea: *"I'll pay more to be 8
miles from work than to be 25 miles out, but how much more is it worth?"* Move
the workplace pin and the zones recompute, which flips the ranking.

### **[→ Try it live](https://jatanmehta19.github.io/BestHome/)**

No sign-up, no API key, nothing to install. Drop the workplace pin anywhere and
watch the ranking reorder.

---

## What's here

Two things share one scoring model:

| | | |
|---|---|---|
| **The demo** | [live](https://jatanmehta19.github.io/BestHome/), source in `site/` | Self-contained HTML page. Synthetic listings, everything adjustable, instant. |
| **The pipeline** | `step*.py` | Scrapes real listings and scores them with traffic-aware Google Maps drive times. Runs locally, needs two API keys. |

If you only want to see what it does, use the demo — it needs nothing installed.
The rest of this page is about running the pipeline on real listings.

---

## Run it on real listings

### Before you start

You need three things, and two of them cost money. Worth knowing up front:

| | |
|---|---|
| **Python 3.9+** | Uses `list[dict]` annotations. 3.9 is the floor. |
| **An Apify account** | The scrape runs on Apify's platform via the `epctex/homes-com-scraper` actor. Running an actor consumes account credits — check [the actor's page](https://apify.com/epctex/homes-com-scraper) for current pricing and whatever free allowance your plan includes. Token: Console → Settings → Integrations. |
| **A Google Maps API key** *(optional)* | For real drive times. Needs a Google Cloud project with **billing enabled** and the **Distance Matrix API** switched on. Google gives a monthly free allowance; past it, you pay per element, and this makes roughly one call per listing. |

**Without the Google key the pipeline still runs.** Step 2 falls back to
straight-line distance × a minutes-per-mile factor and prints that it's doing so.
Rankings stay useful; the minutes aren't real. Start here before you enable
billing anywhere.

### 1. Install

```bash
git clone https://github.com/JatanMehta19/BestHome.git
cd BestHome
pip install -r requirements.txt
```

### 2. Configure

Copy the example config and edit it. Everything personal lives in `config.py`,
which is gitignored.

```bash
cp config_example.py config.py
```

On Windows use `copy config_example.py config.py`.

If you skip this step the pipeline still runs, on the placeholder values in
`config_example.py`, and tells you so on every run.

### 3. Set your keys

Keys come from the environment, never from a file.

```bash
export APIFY_API_TOKEN="apify_api_..."
export GOOGLE_MAPS_API_KEY="AIza..."
```

Windows PowerShell, for this session only:

```bash
$env:APIFY_API_TOKEN = "apify_api_..."
```

Windows, permanently — reopen the terminal afterwards:

```bash
setx APIFY_API_TOKEN "apify_api_..."
```

### 4. Run the three stages

```bash
python step1_scraper.py          # scrape    -> output/raw_listings.json
python step1b_process_json.py    # filter    -> output/listings_clean.csv
python step2_scoring_pipeline.py # score     -> output/listings_scored.csv + report
```

They're separate on purpose. Scraping is the slow, paid part, so once
`raw_listings.json` exists you can re-tune budgets, towns and weights and re-run
steps 1b and 2 as often as you like for free.

### What you get

| File | |
|---|---|
| `output/raw_listings.json` | Everything the scraper returned, untouched. Re-run the later stages from this. |
| `output/listings_clean.csv` | Filtered and flattened: one row per listing, ~35 columns. |
| `output/listings_scored.csv` | The same rows plus commute times, costs and the value score. |
| `output/top_listings_report.txt` | Human-readable ranking. |

The report lists each home with its monthly breakdown — illustrative row, using a
listing from the demo set:

```
  #1    412 Alder Ct, Islip, NY
       VALUE SCORE    : 62.7  |  $  549,999  |  3bd/2ba  |  1728 sqft  |  $318/sqft
       MONTHLY BREAKDOWN:
         Mortgage     : $  3,041  ($494,999 @ 6.23%)
         Tax          : $    639  (annual $7,672)
         Gas (monthly): $    150  ($7.21/day | $1,803/yr)
         Utilities    : $    300  (estimate)
         TOTAL        : $  4,130 / month
```

---

## Using it for your own area

Nothing here is structurally tied to Long Island, but five settings assume it.
Change all of them together, in `config.py`:

| Setting | |
|---|---|
| `START_URLS` | Homes.com town pages to scrape. Browse to a town on homes.com and copy the URL. |
| `CLOSE_TOWNS` / `FAR_TOWNS` | Which towns fall in which budget zone. **Lowercase**, matched exactly against each listing's city. |
| `CLOSE_BUDGET` / `FAR_BUDGET` | The two ceilings. |
| `OFFICE_COORDS` | Where you commute to. Right-click a spot in Google Maps to copy its coordinates. |
| `STATION_GEOCODE_REGION` | Appended to station names before geocoding, e.g. `"Chicagoland, IL"`. A bare station name geocodes to the wrong state often enough to matter. |

**`START_URLS` and the two town sets have to agree.** A town you scrape but don't
list is discarded as `wrong_town`; a town you list but don't scrape contributes
nothing. Step 1b prints both mismatches after every run.

The commuter-rail columns are named `lirr_*` for historical reasons, but the code
just reads whatever stop the listing reports as `commuter rail` — Metra, SEPTA,
Caltrain and the rest work the same way.

---

## Troubleshooting

**"Normalized 0 listings" / empty CSV.** Almost always town names. Matching is an
exact lowercase comparison against the scraper's `city` field, so `"deer park"`
matches and `"Deer Park "` or `"deerpark"` don't. Step 1b prints exactly which
towns it threw away and how many:

```
  -> scraped but in no town list: Selden 3, Lake Grove 2, Nesconset 2
  -> priced out of their zone budget: Ronkonkoma 25, Farmingdale 18
```

Copy the names from that first line into `CLOSE_TOWNS` or `FAR_TOWNS`.

**Everything lands in `over_budget`.** Your ceilings are below the local market.
The second diagnostic line shows the damage by town; raise a budget or widen the
zone radius.

**`ModuleNotFoundError: pandas`.** Installed into a different interpreter than the
one you're running. Check with `python -c "import sys; print(sys.executable)"`.

**Drive times look too high and round.** That's the no-API-key fallback —
straight-line distance × 2.5 min/mi. Step 2 prints `No API key` when this happens.

**`config.py not found`.** Harmless; it's running on the example placeholders.
Copy the file (step 2 above) to use your own settings.

---

## The demo

```bash
python make_demo_data.py   # regenerate the synthetic dataset
python build_site.py       # inline it into site/index.html
```

`site/index.html` is one file with no dependencies and no network calls. Open it
locally, or drop it on any static host unchanged. Fonts come from Google Fonts;
everything else is inline. Pushing a rebuilt `site/` deploys it —
`.github/workflows/pages.yml` publishes to GitHub Pages at the site root.

Adjustable in the page: workplace location (six preset employment centres, or
click the map), near-zone radius, both budget ceilings, distance cutoff, bed/bath
minimums, mortgage rate and down payment, gas price, MPG, commute days and weeks,
utilities, and the four score weights.

---

## How the score works

Four factors, each normalised across the listings that pass your filters, lower
being better, then combined with your weights (default in brackets):

- **Price per square foot** [30%]
- **All-in monthly cost** [40%]
- **Drive time to work** [20%]
- **Drive time to the nearest commuter-rail station** [10%]

Two things worth knowing about what that number means:

**It is relative, not absolute.** A score of 80 means "good *among these
listings*". Change a filter and every number moves. The report and the demo both
say so rather than implying a universal rating.

**Missing data scores worst, not best.** A listing with no square footage gets
the *worst* price-per-sqft score. The obvious implementation — treating missing
sqft as `0` — makes it the *best*, because lower is better. That bug put a
listing with no sqft at the top of the ranking until it was caught.

---

## Why the demo data is synthetic

The demo ships invented listings. This is a deliberate choice, not a shortcut:

- **Licensing.** Real listings come from Homes.com, owned by CoStar, whose terms
  and litigation history put redistribution out of bounds. Scraping for your own
  house hunt is one thing; republishing that data on a public site is another.
- **Third-party privacy.** Scraped listings carry real agents' names and phone
  numbers. None of that belongs in a portfolio demo.
- **Personal privacy.** A live scrape is tied to one person's actual house
  search — their workplace, their budget, their shortlist. The demo deliberately
  covers a different part of Long Island than the pipeline here searches.

So `make_demo_data.py` generates listings whose **distributions** are calibrated
to a real scrape: the price band, median square footage, and effective
property-tax rates of 1.3–1.7% of price. (That tax rate is why property tax
outweighs fuel in nearly every row — a genuinely Long Island result.) Street
names, house numbers and coordinates are invented, and there is no agent data at
all. The generator is seeded, so the demo never shifts underfoot.

The scoring engine the demo runs is the real one — the JavaScript model is
checked against the Python pipeline and agrees to the cent on mortgage and to two
decimals on distance.

Town names, coordinates and stations are real public geography.

---

## Design notes

**No "bring your own API key".** An earlier plan had visitors paste their own
Apify and Google keys into the page. Those keys are billable, and asking strangers
to hand them to an unfamiliar site is a pattern worth distrusting — it would also
mean nobody sees anything until they've signed up for two services. Shipping a
dataset instead means the demo works in the first five seconds.

**Straight-line commute estimates in the demo.** The page multiplies straight-line
distance by an adjustable minutes-per-mile factor, and says so on the control. Real
traffic-aware times need a billed API call per listing, which a public page can't
make. The pipeline uses Google Distance Matrix with `duration_in_traffic`.

**No map tiles.** The map is a hand-drawn SVG with one uniform miles-to-pixels
scale, so the near-zone radius renders as a true circle rather than an ellipse. No
tile server, no key, no tracking, works offline.

---

## Project layout

```
config_example.py          placeholder settings (committed)
config.py                  your real settings (gitignored)
settings.py                loads config.py, falls back to the example

step1_scraper.py           Apify scrape      -> raw_listings.json
step1b_process_json.py     filter + normalise -> listings_clean.csv
step2_scoring_pipeline.py  commute, costs, score -> scored CSV + report
output/                    pipeline output (gitignored)

make_demo_data.py          synthetic dataset generator (seeded)
build_site.py              inlines the data into a single HTML file
site/index.template.html   page source
site/demo_listings.json    generated dataset
site/index.html            built, self-contained — this is the demo

.github/workflows/pages.yml  deploys the demo to GitHub Pages on push
```

Credentials are read from environment variables. Nothing in this repository
contains a key, a real listing, or a personal setting.

## License

MIT — see [LICENSE](LICENSE).
