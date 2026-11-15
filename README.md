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

| | |
|---|---|
| **The demo** ([live](https://jatanmehta19.github.io/BestHome/), source in `site/`) | Self-contained HTML page. Synthetic listings, everything adjustable, instant. |
| **The pipeline** (`step*.py`) | Scrapes live listings and scores them with traffic-aware Google Maps drive times. Private, runs locally. |

### The demo

```bash
python make_demo_data.py   # regenerate the synthetic dataset
python build_site.py       # inline it into site/index.html
```

`site/index.html` is one file with no dependencies and no network calls. Open it
locally, or drop it on any static host unchanged. Fonts come from Google Fonts;
everything else is inline.

Pushing a rebuilt `site/` deploys it — `.github/workflows/pages.yml` publishes
the built files to GitHub Pages at the site root.

Adjustable: workplace location (six preset employment centres, or click the map),
near-zone radius, both budget ceilings, distance cutoff, bed/bath minimums,
mortgage rate and down payment, gas price, MPG, commute days and weeks, utilities,
and the four score weights.

### The pipeline

```bash
pip install -r requirements.txt
copy config_example.py config.py            # then edit it
setx APIFY_API_TOKEN "apify_api_..."        # scraper credentials
setx GOOGLE_MAPS_API_KEY "AIza..."          # drive times (optional)

python step1_scraper.py          # -> output/raw_listings.json
python step1b_process_json.py    # -> output/listings_clean.csv
python step2_scoring_pipeline.py # -> output/listings_scored.csv + report
```

**All tuning lives in `config.py`** — workplace coordinates, the two budget
ceilings, town lists, bed/bath minimums, commute pattern, financial assumptions
and score weights. That file is gitignored, and `settings.py` falls back to the
placeholder values in `config_example.py` so a fresh clone still runs. No script
contains a personal value; nothing identifying gets committed.

Stages are deliberately separate. Scraping is the slow, paid part, so budgets and
weights can be re-tuned and re-scored as often as you like without re-scraping.
Without `GOOGLE_MAPS_API_KEY`, step 2 falls back to straight-line distance × a
minutes-per-mile factor and says so.

Requires `apify-client`, `googlemaps` and `pandas` — see `requirements.txt`.
The demo needs none of them.

---

## How the score works

Four factors, each normalised across the listings that pass your filters, lower
being better, then combined with your weights (default in brackets):

- **Price per square foot** [30%]
- **All-in monthly cost** [40%]
- **Drive time to work** [20%]
- **Drive time to the nearest LIRR station** [10%]

Two things worth knowing about what that number means:

**It is relative, not absolute.** A score of 80 means "good *among these
listings*". Change a filter and every number moves. The report and the demo both
say so rather than implying a universal rating.

**Missing data scores worst, not best.** A listing with no square footage gets
the *worst* price-per-sqft score. The obvious implementation — treating missing
sqft as `0` — makes it the *best*, because lower is better. That bug had a
no-sqft listing ranked #1 overall until it was fixed; it now sits at #6, where it
belongs on the strength of its genuinely low monthly cost.

---

## Why the demo data is synthetic

The demo ships invented listings. This is a deliberate choice, not a shortcut:

- **Licensing.** Real listings come from Homes.com, owned by CoStar, whose terms
  and litigation history put redistribution out of bounds. Scraping for your own
  house hunt is one thing; republishing that data on a public site is another.
- **Third-party privacy.** Scraped listings carry real agents' names and phone
  numbers. None of that belongs in a portfolio demo.
- **Personal privacy.** A live scrape is tied to one person's actual house
  search — their workplace, their budget, their shortlist.

So `make_demo_data.py` generates listings whose **distributions** are calibrated
to the real scrape: town-level price quartiles, median square footage, and
effective property-tax rates of 1.3–1.7% of price. (That tax rate is why property
tax outweighs fuel in nearly every row — a genuinely Long Island result.) Street
names, house numbers and coordinates are invented. There is no agent data at all.
The generator is seeded, so the demo never shifts underfoot.

The scoring engine the demo runs is the real one — the JavaScript model is
checked against the Python pipeline and agrees to the cent on mortgage and to two
decimals on distance.

Town names, coordinates and LIRR stations are real public geography.

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
.github/workflows/pages.yml  deploys the demo to GitHub Pages on push

config_example.py          placeholder settings (committed)
config.py                  your real settings (gitignored)
settings.py                loads config.py, falls back to the example

make_demo_data.py          synthetic dataset generator (seeded)
build_site.py              inlines the data into a single HTML file
site/index.template.html   page source
site/demo_listings.json    generated dataset
site/index.html            built, self-contained — this is the demo

step1_scraper.py           Apify scrape -> raw_listings.json
step1b_process_json.py     filter + normalise -> listings_clean.csv
step2_scoring_pipeline.py  commute, costs, score -> scored CSV + report
output/                    pipeline output (gitignored)
```

Credentials are read from environment variables. Nothing in this repository
contains a key, a real listing, or a personal setting.

## License

MIT — see [LICENSE](LICENSE).
