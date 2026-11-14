#!/usr/bin/env python3
"""
============================================================
 Commute Cost Ranker - site build
============================================================
 site/index.template.html + site/demo_listings.json
   -> site/index.html   (one self-contained file)

 The data is inlined rather than fetched so the page needs no
 server, no network and no API key: open index.html from disk,
 or drop it on GitHub Pages / Netlify as-is.

 USAGE:
   python make_demo_data.py    # regenerate the dataset
   python build_site.py        # inline it into index.html
============================================================
"""
import json
import os
import sys

TEMPLATE = os.path.join("site", "index.template.html")
DATA     = os.path.join("site", "demo_listings.json")
OUT      = os.path.join("site", "index.html")
TOKEN    = "__DEMO_DATA__"


def main():
    for path in (TEMPLATE, DATA):
        if not os.path.exists(path):
            print("ERROR: missing " + path)
            return 1

    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()

    if TOKEN not in html:
        print("ERROR: " + TOKEN + " placeholder not found in " + TEMPLATE)
        return 1

    with open(DATA, encoding="utf-8") as f:
        payload = json.load(f)

    # Compact, and escaped so the JSON can never terminate the <script> block
    # early or be read as HTML by the parser.
    blob = json.dumps(payload, separators=(",", ":"))
    blob = blob.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    html = html.replace(TOKEN, blob)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    kb = os.path.getsize(OUT) / 1024
    print("Built " + OUT + "  (" + format(kb, ".1f") + " KB, " +
          str(payload["count"]) + " listings inlined)")
    print("  Open it directly in a browser - no server needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
