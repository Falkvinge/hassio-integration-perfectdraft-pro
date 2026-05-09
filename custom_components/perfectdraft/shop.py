"""Slow, polite PerfectDraft product-page scraper."""
from __future__ import annotations

import asyncio
import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin
import urllib.request

import aiohttp

SHOP_USER_AGENT = (
    "HomeAssistant-PerfectDraft-Pro/0.6 "
    "(local Home Assistant integration; low-frequency product metadata cache)"
)
PERFECTDRAFT_KEGS_URL = (
    "https://www.perfectdraft.com/en-gb/perfect-draft-range/perfect-draft-kegs"
)


def _clean_text(value: str | None) -> str | None:
    """Return compact plain text from HTML-ish input."""
    if not value:
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _fetch_text(url: str) -> str:
    """Fetch text with urllib to tolerate PerfectDraft's very large headers."""
    request = urllib.request.Request(url, headers={"User-Agent": SHOP_USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


async def _async_fetch_text(url: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_text, url)


def _meta(page: str, itemprop: str) -> str | None:
    match = re.search(
        rf'<meta\s+itemprop="{re.escape(itemprop)}"\s+content="([^"]*)"',
        page,
        re.IGNORECASE,
    )
    return _clean_text(match.group(1)) if match else None


def _json_string(page: str, key: str) -> str | None:
    match = re.search(
        rf'"{re.escape(key)}"\s*:\s*("(?:\\.|[^"\\])*")',
        page,
    )
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return _clean_text(value)


def _json_scalar(page: str, key: str) -> str | None:
    match = re.search(
        rf'"{re.escape(key)}"\s*:\s*("(?:\\.|[^"\\])*"|null|true|false|-?\d+(?:\.\d+)?)',
        page,
    )
    if not match:
        return None
    raw = match.group(1)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if value is None:
        return None
    return str(value)


def _json_object(page: str, key: str) -> dict[str, Any] | None:
    marker = f'"{key}":'
    index = page.find(marker)
    if index < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(page[index + len(marker) :].lstrip())
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _product_spec(page: str, code: str) -> str | None:
    match = re.search(
        rf"<li[^>]+data-code={re.escape(code)}[^>]*>.*?<span>(.*?)</span>",
        page,
        re.IGNORECASE | re.DOTALL,
    )
    return _clean_text(match.group(1)) if match else None


def _absolute_image_url(product_url: str, value: str | None) -> str | None:
    if not value:
        return None
    return urljoin(product_url, value)


def _json_ld_products(page: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        page,
        re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("@type") == "Product":
            products.append(payload)
    return products


def parse_shop_product_page(product_url: str, page: str) -> dict[str, Any]:
    """Extract stable card data plus volatile shop fields from a product page."""
    data: dict[str, Any] = {}

    image = _json_string(page, "image") or _meta(page, "image")
    short_description = (
        _json_string(page, "meta_description")
        or _meta(page, "description")
        or _json_string(page, "short_description")
    )
    quantity = _json_object(page, "quantity_and_stock_status")

    data.update(
        {
            "shop_url": product_url,
            "website_product_id": _json_scalar(page, "productId"),
            "bp_product_id": _json_scalar(page, "bp_product_id"),
            "sku": _meta(page, "sku") or _json_string(page, "sku"),
            "gtin": _json_string(page, "gtin"),
            "sap_product_code": _json_string(page, "sap_product_code"),
            "image_url": _absolute_image_url(product_url, image),
            "food_pairings": _json_string(page, "food_pairings"),
            "short_description": short_description,
            "plato": _json_string(page, "plato"),
            "recommended_temperature": (
                _json_string(page, "serving_temp")
                or _product_spec(page, "serving_temp")
            ),
            "price": _json_string(page, "price") or _meta(page, "price"),
            "price_per_pint": _product_spec(page, "priceper_measure"),
        }
    )

    if quantity:
        in_stock = quantity.get("is_in_stock")
        data["stock_state"] = "in_stock" if in_stock else "out_of_stock"
        if quantity.get("qty") is not None:
            data["stock_quantity"] = quantity.get("qty")

    for product in _json_ld_products(page):
        offers = product.get("offers") or {}
        rating = product.get("aggregateRating") or {}
        if isinstance(offers, dict):
            availability = str(offers.get("availability") or "")
            if availability:
                data["stock_state"] = (
                    "in_stock" if availability.endswith("InStock") else "out_of_stock"
                )
            if offers.get("price") is not None:
                data["price"] = str(offers["price"])
            if offers.get("priceCurrency") is not None:
                data["price_currency"] = str(offers["priceCurrency"])
        if isinstance(rating, dict):
            if rating.get("reviewCount") is not None:
                data["review_count"] = int(rating["reviewCount"])
            if rating.get("ratingValue") is not None:
                value = float(rating["ratingValue"])
                data["review_rating"] = value / 20 if value > 5 else value

    return {key: value for key, value in data.items() if value not in (None, "")}


async def async_fetch_shop_product(
    session: aiohttp.ClientSession,
    product_url: str,
) -> dict[str, Any]:
    """Fetch and parse one PerfectDraft product page."""
    page = await _async_fetch_text(product_url)
    return parse_shop_product_page(product_url, page)


def parse_available_beer_count(page: str) -> int | None:
    """Extract the available keg count from the curated PerfectDraft range page."""
    match = re.search(r'"numberOfItems"\s*:\s*(\d+)', page)
    if match:
        return int(match.group(1))

    match = re.search(
        r"PerfectDraft Kegs\s+(\d+)\s+item",
        page,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


async def async_fetch_available_beer_count(
    session: aiohttp.ClientSession,
) -> int | None:
    """Fetch the advertised PerfectDraft keg range count."""
    page = await _async_fetch_text(PERFECTDRAFT_KEGS_URL)
    return parse_available_beer_count(page)


def _algolia_config(page: str) -> dict[str, Any] | None:
    match = re.search(
        r"window\.algoliaConfig\s*=\s*(\{.*?\});\s*// Update cached",
        page,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


async def async_fetch_available_beer_catalogue(
    session: aiohttp.ClientSession,
) -> dict[str, Any]:
    """Fetch the current curated PerfectDraft keg range summary."""
    page = await _async_fetch_text(PERFECTDRAFT_KEGS_URL)

    count = parse_available_beer_count(page)
    config = _algolia_config(page)
    if not config:
        return {
            "source_url": PERFECTDRAFT_KEGS_URL,
            "available_beers": count,
            "beer_names": [],
        }

    app_id = config["applicationId"]
    api_key = config["apiKey"]
    index_name = f"{config['indexName']}_products"
    category_id = str((config.get("request") or {}).get("categoryId") or "415")
    url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index_name}/query"
    headers = {
        "X-Algolia-Application-Id": app_id,
        "X-Algolia-API-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": SHOP_USER_AGENT,
    }
    payload = {
        "query": "",
        "hitsPerPage": 100,
        "page": 0,
        "facetFilters": [f"categoryIds:{category_id}"],
    }

    async with session.post(url, headers=headers, json=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()

    products = [_product_summary(hit) for hit in data.get("hits", [])]
    products = [product for product in products if product.get("name")]
    products.sort(key=lambda item: str(item["name"]).casefold())
    return {
        "source_url": PERFECTDRAFT_KEGS_URL,
        "available_beers": int(data.get("nbHits") or count or len(products)),
        "beer_names": [product["name"] for product in products],
        "products": products,
    }


def _product_summary(hit: dict[str, Any]) -> dict[str, Any]:
    """Return useful non-sensitive fields from an Algolia product hit."""
    price = hit.get("price") or {}
    gbp = price.get("GBP") if isinstance(price, dict) else {}
    group_price = gbp.get("group_0") if isinstance(gbp, dict) else None
    return {
        "name": hit.get("app_product_name") or hit.get("name"),
        "product_name": hit.get("name"),
        "website_product_id": str(hit.get("objectID")) if hit.get("objectID") else None,
        "url": hit.get("url"),
        "sku": hit.get("sku"),
        "image_url": hit.get("image_url") or hit.get("thumbnail_url"),
        "brewery": hit.get("brewery"),
        "style": hit.get("style"),
        "country": hit.get("country"),
        "abv": hit.get("alcoholic_content"),
        "size": hit.get("bottle_size"),
        "price": str(group_price) if group_price is not None else None,
        "stock_state": "in_stock" if hit.get("in_stock") else "out_of_stock",
        "review_count": hit.get("reviews_count"),
        "review_rating": (
            round(float(hit["rating_summary"]) / 20, 2)
            if hit.get("rating_summary") is not None
            else None
        ),
    }
