import asyncio
import httpx
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
from dateutil import parser as date_parser
from collections import Counter

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
    "Referer": "https://www.wildberries.ru/catalog/0/search.aspx",
    "Origin": "https://www.wildberries.ru",
    "Connection": "keep-alive",
}

SEARCH_URL = (
    "https://search.wb.ru/exactmatch/ru/common/v4/search"
    "?appType=1&curr=rub&dest=-1257786&page={page}"
    "&query={query}&resultset=catalog&sort=popular&spp=0&suppressSpellcheck=false"
)
CARD_URL = (
    "https://card.wb.ru/cards/v1/detail"
    "?appType=1&curr=rub&dest=-1257786&spp=0&nm={article_id}"
)
FEEDBACK_URL = (
    "https://feedbacks1.wb.ru/feedbacks/v1/{article_id}"
    "?take={take}&skip={skip}&order=date&isSorted=true"
)

REQUEST_SEMAPHORE = asyncio.Semaphore(3)

async def _fetch(client: httpx.AsyncClient, url: str, retries: int = 2) -> Optional[dict]:
    for attempt in range(retries + 1):
        try:
            async with REQUEST_SEMAPHORE:
                await asyncio.sleep(random.uniform(0.6, 1.2))
                resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=20.0)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (403, 429, 503):
                    await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
        except Exception:
            if attempt < retries:
                await asyncio.sleep(1.5)
    return None

async def search_wb(client: httpx.AsyncClient, query: str, pages: int = 2) -> List[Dict[str, Any]]:
    products = []
    for page in range(1, pages + 1):
        url = SEARCH_URL.format(page=page, query=query.replace(" ", "%20"))
        data = await _fetch(client, url)
        if not data:
            continue
        items = data.get("data", {}).get("products", [])
        for p in items:
            products.append({
                "id": p.get("id"),
                "name": p.get("name", "").strip(),
                "brand": p.get("brand", ""),
                "price": ((p.get("salePriceU", 0) or p.get("priceU", 0)) / 100),
                "rating": p.get("rating", 0),
                "feedbacks": p.get("feedbacks", 0),
                "supplier": p.get("supplier", ""),
            })
    return products

async def get_card_details(client: httpx.AsyncClient, article_id: int) -> Optional[Dict[str, Any]]:
    url = CARD_URL.format(article_id=article_id)
    data = await _fetch(client, url)
    if not data:
        return None
    prods = data.get("data", {}).get("products", [])
    if not prods:
        return None
    p = prods[0]
    return {
        "id": article_id,
        "name": p.get("name", "").strip(),
        "price": ((p.get("salePriceU", 0) or p.get("priceU", 0)) / 100),
        "rating": p.get("rating", 0),
        "feedbacks": p.get("feedbacks", 0),
    }

async def get_feedbacks(client: httpx.AsyncClient, article_id: int, max_feedbacks: int = 100) -> List[Dict[str, Any]]:
    all_fb = []
    page = 0
    batch = 20
    while len(all_fb) < max_feedbacks:
        url = FEEDBACK_URL.format(article_id=article_id, take=batch, skip=page * batch)
        data = await _fetch(client, url)
        if not data:
            break
        feedbacks = data.get("feedbacks", [])
        if not feedbacks:
            break
        for fb in feedbacks:
            all_fb.append({
                "date": fb.get("createdDate", ""),
                "rating": fb.get("productValuation", 0),
                "text": (fb.get("text", "") or "")[:300],
                "votes": fb.get("votes", {}).get("count", 0),
            })
        page += 1
    return all_fb[:max_feedbacks]

def analyze_feedbacks(feedbacks: List[Dict[str, Any]], price: float) -> Optional[Dict[str, Any]]:
    if not feedbacks:
        return None
    dates = []
    for fb in feedbacks:
        d_str = fb.get("date", "")
        if not d_str:
            continue
        try:
            dt = date_parser.isoparse(d_str.replace("Z", "+00:00"))
            dates.append(dt.date())
        except Exception:
            continue
    if not dates:
        return None
    dates.sort()
    today = datetime.now().date()
    last_30 = [d for d in dates if d >= today - timedelta(days=30)]
    last_7 = [d for d in dates if d >= today - timedelta(days=7)]
    low_mult = 5.5
    high_mult = 10.0
    reviews_30d = len(last_30)
    reviews_7d = len(last_7)
    est_orders_30d_low = int(reviews_30d * low_mult)
    est_orders_30d_high = int(reviews_30d * high_mult)
    est_orders_7d_low = int(reviews_7d * low_mult)
    est_orders_7d_high = int(reviews_7d * high_mult)
    return {
        "total_reviews": len(dates),
        "reviews_last_30d": reviews_30d,
        "reviews_last_7d": reviews_7d,
        "first_review": str(min(dates)),
        "last_review": str(max(dates)),
        "estimated_orders_30d_low": est_orders_30d_low,
        "estimated_orders_30d_high": est_orders_30d_high,
        "estimated_orders_7d_low": est_orders_7d_low,
        "estimated_orders_7d_high": est_orders_7d_high,
        "estimated_revenue_30d_low": round(est_orders_30d_low * price, 2),
        "estimated_revenue_30d_high": round(est_orders_30d_high * price, 2),
        "estimated_revenue_7d_low": round(est_orders_7d_low * price, 2),
        "estimated_revenue_7d_high": round(est_orders_7d_high * price, 2),
    }

async def analyze_niche(query: str, top_n: int = 10, max_feedbacks: int = 80, search_pages: int = 2) -> Dict[str, Any]:
    start_time = datetime.utcnow().isoformat()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        search_results = await search_wb(client, query, pages=search_pages)
        if not search_results:
            return {
                "query": query,
                "analyzed_at": start_time,
                "error": "No search results or blocked by WB",
                "competitors": [],
                "market_summary": {},
            }
        seen = set()
        candidates = []
        for item in search_results:
            aid = item["id"]
            if aid not in seen and item.get("feedbacks", 0) > 0:
                seen.add(aid)
                candidates.append(item)
            if len(candidates) >= top_n:
                break
        competitors = []
        for item in candidates:
            art = item["id"]
            details = await get_card_details(client, art)
            if not details:
                details = item
            fbs = await get_feedbacks(client, art, max_feedbacks=max_feedbacks)
            sales = analyze_feedbacks(fbs, details["price"])
            competitors.append({
                "article_id": art,
                "name": details["name"],
                "brand": item.get("brand", ""),
                "price": details["price"],
                "rating": details["rating"],
                "total_feedbacks_wb": details["feedbacks"],
                "scraped_feedbacks": len(fbs),
                "sales_estimate": sales,
            })
    valid = [c for c in competitors if c["sales_estimate"]]
    summary = {}
    if valid:
        prices = [c["price"] for c in valid]
        orders_low_30 = [c["sales_estimate"]["estimated_orders_30d_low"] for c in valid]
        orders_high_30 = [c["sales_estimate"]["estimated_orders_30d_high"] for c in valid]
        rev_low_30 = [c["sales_estimate"]["estimated_revenue_30d_low"] for c in valid]
        rev_high_30 = [c["sales_estimate"]["estimated_revenue_30d_high"] for c in valid]
        median_orders_low = sorted(orders_low_30)[len(orders_low_30) // 2]
        median_orders_high = sorted(orders_high_30)[len(orders_high_30) // 2]
        summary = {
            "competitors_analyzed": len(valid),
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "median_orders_30d_low": median_orders_low,
            "median_orders_30d_high": median_orders_high,
            "total_market_revenue_30d_low": round(sum(rev_low_30), 2),
            "total_market_revenue_30d_high": round(sum(rev_high_30), 2),
            "new_product_forecast": {
                "pessimistic_1pct_orders_30d": max(1, int(median_orders_low * 0.01)),
                "realistic_3pct_orders_30d": max(1, int(median_orders_low * 0.03)),
                "optimistic_10pct_orders_30d": max(1, int(median_orders_high * 0.10)),
                "pessimistic_revenue_30d": round(max(1, int(median_orders_low * 0.01)) * (sum(prices)/len(prices)), 2),
                "realistic_revenue_30d": round(max(1, int(median_orders_low * 0.03)) * (sum(prices)/len(prices)), 2),
                "optimistic_revenue_30d": round(max(1, int(median_orders_high * 0.10)) * (sum(prices)/len(prices)), 2),
            }
        }
    return {
        "query": query,
        "analyzed_at": start_time,
        "market_summary": summary,
        "competitors": competitors,
    }
