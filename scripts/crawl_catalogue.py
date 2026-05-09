#!/usr/bin/env python3
"""Slowly crawl PerfectDraft keg pages and write parsed catalogue data.

This is a developer maintenance script. It is intentionally not used by the
Home Assistant integration at runtime.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOP_PATH = ROOT / "custom_components" / "perfectdraft" / "shop.py"
DEFAULT_OUTPUT = ROOT / "catalogue-crawl.json"
DEFAULT_DELAY = 90
USER_AGENT = (
    "PerfectDraftCatalogueMaintenance/0.1 "
    "(manual low-frequency catalogue update script)"
)


def _load_shop_module():
    spec = importlib.util.spec_from_file_location("perfectdraft_shop", SHOP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SHOP_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def _sitemap_urls(source: str) -> list[str]:
    xml = _fetch(source)
    root = ET.fromstring(xml)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    return [
        loc.text.strip()
        for loc in root.findall(f".//{namespace}loc")
        if loc.text
    ]


def _product_urls(sitemap: str) -> list[str]:
    urls: list[str] = []
    pending = [sitemap]
    seen: set[str] = set()
    while pending:
        source = pending.pop(0)
        if source in seen:
            continue
        seen.add(source)
        for url in _sitemap_urls(source):
            if url.endswith(".xml"):
                pending.append(url)
            elif _looks_like_single_keg_url(url):
                urls.append(url)
    return sorted(set(urls))


def _looks_like_single_keg_url(url: str) -> bool:
    lower = url.lower()
    if not re.search(r"/en-gb/.*6l.*keg", lower):
        return False
    if re.search(r"\d+\s*-?\s*x\s*-?\s*6l", lower) or "6l-kegs" in lower:
        return False
    return not any(
        excluded in lower
        for excluded in ("pack", "bundle", "machine", "starter", "multipack")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sitemap",
        default="https://www.perfectdraft.com/en-gb/sitemap.xml",
        help="Sitemap URL to seed the crawl from.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="JSON output path.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help="Seconds to wait between product-page fetches.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of product pages to fetch. 0 means no limit.",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only list matching product URLs without fetching product pages.",
    )
    args = parser.parse_args()

    shop = _load_shop_module()
    urls = _product_urls(args.sitemap)
    if args.limit:
        urls = urls[: args.limit]

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_sitemap": args.sitemap,
        "products": {},
        "errors": {},
    }

    if args.discover_only:
        output["product_urls"] = urls
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True))
        print(f"Wrote {len(urls)} discovered product URLs to {args.output}")
        return 0

    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}", flush=True)
        try:
            page = _fetch(url)
            data = shop.parse_shop_product_page(url, page)
            key = data.get("bp_product_id") or data.get("website_product_id") or url
            output["products"][key] = data
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            output["errors"][url] = str(err)

        args.output.write_text(json.dumps(output, indent=2, sort_keys=True))
        if index < len(urls):
            time.sleep(args.delay + random.uniform(0, min(args.delay * 0.2, 30)))

    print(f"Wrote {len(output['products'])} products to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
