from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import _bootstrap
from narralytica.config import load_dotenv
from soso_client import BinanceTerminalClient, SoSoValueTerminalClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DATA_DIR = PROJECT_ROOT / "website_data" / "terminal"

CORE_ASSETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "LINK", "AVAX", "SUI"]
HERO_ASSETS = ["BTC", "ETH"]
INDEX_TICKERS = ["ssiMAG7", "ssiLayer1", "ssiAI", "ssiMeme", "ssiDeFi", "ssiRWA"]
WATCHLIST_STOCKS = ["MSTR", "COIN", "MARA", "RIOT", "HUT", "SMLR"]
TREASURY_TICKERS = ["MSTR", "MARA", "COIN", "RIOT", "HUT"]
ETF_TYPE_BY_ASSET = {"BTC": "BTC", "ETH": "ETH"}
BINANCE_SYMBOL_BY_ASSET = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}

T = TypeVar("T")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _iso_from_ms(value: Any) -> str | None:
    timestamp = _safe_int(value)
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat()


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous


def _sorted_desc(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: _safe_float(row.get(field)) or float("-inf"), reverse=True)


def _normalize_etf_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows[:5]:
        normalized.append(
            {
                "date": row.get("date"),
                "totalNetInflow": _safe_float(row.get("total_net_inflow")),
                "totalValueTraded": _safe_float(row.get("total_value_traded")),
                "totalNetAssets": _safe_float(row.get("total_net_assets")),
                "cumulativeNetInflow": _safe_float(row.get("cum_net_inflow")),
            }
        )
    return normalized


def _normalize_positioning(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"available": False, "latest": None, "history": []}

    ordered = sorted(rows, key=lambda row: int(row.get("timestamp", 0)))
    history: list[dict[str, Any]] = []
    for row in ordered:
        history.append(
            {
                "timestamp": _safe_int(row.get("timestamp")),
                "timestampIso": _iso_from_ms(row.get("timestamp")),
                "longShortRatio": _safe_float(row.get("longShortRatio")),
                "longAccountShare": _safe_float(row.get("longAccount")),
                "shortAccountShare": _safe_float(row.get("shortAccount")),
            }
        )

    return {"available": True, "latest": history[-1], "history": history}


def _normalize_market_snapshot(asset: str, currency_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset": asset,
        "currencyId": currency_id,
        "price": _safe_float(snapshot.get("price")),
        "changePct24h": _safe_float(snapshot.get("change_pct_24h")),
        "turnover24h": _safe_float(snapshot.get("turnover_24h")),
        "turnoverRate": _safe_float(snapshot.get("turnover_rate")),
        "high24h": _safe_float(snapshot.get("high_24h")),
        "low24h": _safe_float(snapshot.get("low_24h")),
        "marketCap": _safe_float(snapshot.get("marketcap")),
        "fdv": _safe_float(snapshot.get("fdv")),
        "marketCapRank": _safe_int(snapshot.get("marketcap_rank")),
        "ath": _safe_float(snapshot.get("ath")),
        "athDate": _iso_from_ms(snapshot.get("ath_date")),
        "downFromAth": _safe_float(snapshot.get("down_from_ath")),
        "cycleLow": _safe_float(snapshot.get("cycle_low")),
        "cycleLowDate": _iso_from_ms(snapshot.get("cycle_low_date")),
        "upFromCycleLow": _safe_float(snapshot.get("up_from_cycle_low")),
    }


def _normalize_pair(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "base": row.get("base"),
        "target": row.get("target"),
        "market": row.get("market"),
        "price": _safe_float(row.get("price")),
        "turnover24h": _safe_float(row.get("turnover_24h")),
        "costToMoveUpUsd": _safe_float(row.get("cost_to_move_up_usd")),
        "costToMoveDownUsd": _safe_float(row.get("cost_to_move_down_usd")),
    }


def _normalize_news_item(row: dict[str, Any], *, hot: bool = False) -> dict[str, Any]:
    release_key = "create_time" if hot and row.get("create_time") is not None else "release_time"
    timestamp = _safe_int(row.get(release_key))
    content = _strip_html(str(row.get("content", "") or ""))
    return {
        "id": str(row.get("id", "")),
        "title": str(row.get("title", "") or "").strip(),
        "contentExcerpt": content[:277] + "..." if len(content) > 280 else content,
        "timestamp": timestamp,
        "timestampIso": _iso_from_ms(timestamp),
        "sourceLink": row.get("source_link"),
        "originalLink": row.get("original_link"),
        "author": row.get("author"),
        "nickName": row.get("nick_name"),
        "category": row.get("category"),
        "tags": row.get("tags", []),
        "matchedCurrencies": row.get("matched_currencies", []),
        "featureImage": row.get("feature_image"),
        "impressionCount": _safe_int(row.get("impression_count")),
        "likeCount": _safe_int(row.get("like_count")),
        "replyCount": _safe_int(row.get("reply_count")),
        "retweetCount": _safe_int(row.get("retweet_count")),
        "sourceType": "hot" if hot else "feed",
    }


def _normalize_index_snapshot(ticker: str, snapshot: dict[str, Any], constituents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "price": _safe_float(snapshot.get("price")),
        "changePct24h": _safe_float(snapshot.get("change_pct_24h") or snapshot.get("24h_change_pct")),
        "roi7d": _safe_float(snapshot.get("roi_7d") or snapshot.get("7day_roi")),
        "roi1m": _safe_float(snapshot.get("roi_1m") or snapshot.get("1month_roi")),
        "roi3m": _safe_float(snapshot.get("roi_3m") or snapshot.get("3month_roi")),
        "roi1y": _safe_float(snapshot.get("roi_1y") or snapshot.get("1year_roi")),
        "ytd": _safe_float(snapshot.get("ytd")),
        "topConstituents": [
            {
                "currencyId": row.get("currency_id"),
                "symbol": row.get("symbol"),
                "weight": _safe_float(row.get("weight")),
            }
            for row in constituents[:5]
        ],
    }


def _normalize_crypto_stock(stock: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": stock.get("ticker"),
        "name": stock.get("name"),
        "exchange": stock.get("exchange"),
        "sector": stock.get("sector"),
        "listingTime": stock.get("listing_time"),
        "price": _safe_float(snapshot.get("mkt_price")),
        "marketStatus": snapshot.get("mkt_status"),
        "volume": _safe_float(snapshot.get("volume")),
        "turnover": _safe_float(snapshot.get("turnover")),
        "peTtm": _safe_float(snapshot.get("pe_ttm")),
        "pb": _safe_float(snapshot.get("pb")),
    }


def _normalize_treasury_entry(company: dict[str, Any], purchases: list[dict[str, Any]]) -> dict[str, Any]:
    latest = purchases[0] if purchases else {}
    return {
        "ticker": company.get("ticker"),
        "name": company.get("name"),
        "listLocation": company.get("list_location"),
        "latestPurchaseDate": latest.get("date"),
        "btcHolding": _safe_float(latest.get("btc_holding")),
        "btcAcquired": _safe_float(latest.get("btc_acq")),
        "acquisitionCost": _safe_float(latest.get("acq_cost")),
        "avgBtcCost": _safe_float(latest.get("avg_btc_cost")),
        "recentPurchases": [
            {
                "date": row.get("date"),
                "btcHolding": _safe_float(row.get("btc_holding")),
                "btcAcquired": _safe_float(row.get("btc_acq")),
                "acquisitionCost": _safe_float(row.get("acq_cost")),
                "avgBtcCost": _safe_float(row.get("avg_btc_cost")),
            }
            for row in purchases[:3]
        ],
    }


def _normalize_token_economics(asset: str, economics: dict[str, Any], supply: list[dict[str, Any]]) -> dict[str, Any]:
    unlock = economics.get("token_unlock") if isinstance(economics.get("token_unlock"), dict) else {}
    timeline = economics.get("unlock_timeline") if isinstance(economics.get("unlock_timeline"), list) else []
    allocation = economics.get("token_allocation") if isinstance(economics.get("token_allocation"), list) else []

    next_unlocks: list[dict[str, Any]] = []
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    for row in timeline:
        if not isinstance(row, dict):
            continue
        timestamp = _safe_int(row.get("timestamp"))
        if timestamp is not None and timestamp < now_ms:
            continue
        vestings = row.get("vestings") if isinstance(row.get("vestings"), list) else []
        total_amount = sum(_safe_float(item.get("amount")) or 0 for item in vestings if isinstance(item, dict))
        next_unlocks.append(
            {
                "timestamp": timestamp,
                "timestampIso": _iso_from_ms(timestamp),
                "totalAmount": total_amount,
                "vestings": [
                    {
                        "label": item.get("label"),
                        "amount": _safe_float(item.get("amount")),
                    }
                    for item in vestings[:4]
                    if isinstance(item, dict)
                ],
            }
        )

    supply_rows: list[dict[str, Any]] = []
    for row in supply[:12]:
        supply_rows.append(
            {
                "timestamp": _safe_int(row.get("timestamp") or row.get("date")),
                "timestampIso": _iso_from_ms(row.get("timestamp") or row.get("date")),
                "circulatingSupply": _safe_float(row.get("circulating_supply")),
                "totalSupply": _safe_float(row.get("total_supply")),
                "maxSupply": _safe_float(row.get("max_supply")),
            }
        )

    return {
        "asset": asset,
        "unlocked": _safe_float(unlock.get("unlocked")),
        "totalLocked": _safe_float(unlock.get("total_locked")),
        "topAllocations": [
            {
                "holder": row.get("holder"),
                "percentage": _safe_float(row.get("percentage")),
            }
            for row in allocation[:5]
            if isinstance(row, dict)
        ],
        "nextUnlocks": sorted(next_unlocks, key=lambda row: row.get("timestamp") or 0)[:5],
        "supplyHistory": supply_rows,
    }


def _call_with_capture(
    errors: list[dict[str, str]],
    *,
    source: str,
    fn: Callable[[], T],
    fallback: T,
) -> T:
    try:
        return fn()
    except Exception as exc:
        errors.append({"source": source, "error": str(exc)})
        return fallback


def _build_currency_map(soso: SoSoValueTerminalClient, errors: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    rows = _call_with_capture(errors, source="sosovalue_currencies", fn=soso.get_currencies, fallback=[])
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol:
            mapping[symbol] = row
    return mapping


def _build_asset_bundle(
    soso: SoSoValueTerminalClient,
    binance: BinanceTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
    *,
    asset: str,
) -> dict[str, Any]:
    currency_id = str(currency_map.get(asset, {}).get("currency_id", ""))
    snapshot = _call_with_capture(
        errors,
        source=f"{asset.lower()}_market_snapshot",
        fn=lambda: soso.get_currency_market_snapshot(currency_id),
        fallback={},
    ) if currency_id else {}
    pairs = _call_with_capture(
        errors,
        source=f"{asset.lower()}_pairs",
        fn=lambda: soso.get_currency_pairs(currency_id, page_size=5),
        fallback=[],
    ) if currency_id else []
    klines = _call_with_capture(
        errors,
        source=f"{asset.lower()}_klines",
        fn=lambda: soso.get_currency_klines(currency_id, limit=7),
        fallback=[],
    ) if currency_id else []
    news = _call_with_capture(
        errors,
        source=f"{asset.lower()}_news",
        fn=lambda: soso.get_news(currency_id=currency_id, page_size=5),
        fallback=[],
    ) if currency_id else []

    etf_history_rows: list[dict[str, Any]] = []
    etf_list_rows: list[dict[str, Any]] = []
    if asset in ETF_TYPE_BY_ASSET:
        etf_symbol = ETF_TYPE_BY_ASSET[asset]
        etf_history_rows = _call_with_capture(
            errors,
            source=f"{asset.lower()}_etf_summary_history",
            fn=lambda: soso.get_etf_summary_history(etf_symbol, country_code="US", limit=5),
            fallback=[],
        )
        etf_list_rows = _call_with_capture(
            errors,
            source=f"{asset.lower()}_etf_list",
            fn=lambda: soso.get_etf_list(etf_symbol, country_code="US"),
            fallback=[],
        )

    positioning_rows = []
    if asset in BINANCE_SYMBOL_BY_ASSET:
        positioning_rows = _call_with_capture(
            errors,
            source=f"{asset.lower()}_binance_long_short",
            fn=lambda: binance.get_global_long_short_ratio(BINANCE_SYMBOL_BY_ASSET[asset], period="1d", limit=5),
            fallback=[],
        )

    latest_etf = etf_history_rows[0] if etf_history_rows else {}
    return {
        "asset": asset,
        "currencyId": currency_id or None,
        "snapshot": _normalize_market_snapshot(asset, currency_id, snapshot) if snapshot else None,
        "topPairs": [_normalize_pair(row) for row in pairs[:3]],
        "dailyKlines": [
            {
                "timestamp": _safe_int(row.get("timestamp")),
                "timestampIso": _iso_from_ms(row.get("timestamp")),
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": _safe_float(row.get("volume")),
            }
            for row in klines[:7]
        ],
        "headlineNews": [_normalize_news_item(row) for row in news[:3]],
        "etf": {
            "dailyNetInflow": _safe_float(latest_etf.get("total_net_inflow")),
            "history5d": _normalize_etf_history(etf_history_rows),
            "listedTickers": etf_list_rows[:10],
        },
        "positioning": _normalize_positioning(positioning_rows),
    }


def _build_hero_payload(
    soso: SoSoValueTerminalClient,
    binance: BinanceTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    assets = {
        asset: _build_asset_bundle(soso, binance, currency_map, errors, asset=asset)
        for asset in HERO_ASSETS
    }
    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "assets": assets,
        "errors": errors,
    }


def _build_overview_payload(
    soso: SoSoValueTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    fear_greed = _call_with_capture(
        errors,
        source="analysis_fgi_indicator",
        fn=lambda: soso.get_analysis_chart("fgi_indicator", limit=7),
        fallback=[],
    )
    total_market_cap = _call_with_capture(
        errors,
        source="analysis_total_crypto_market_cap",
        fn=lambda: soso.get_analysis_chart("total_crypto_market_cap", limit=7),
        fallback=[],
    )
    stablecoin_mcap = _call_with_capture(
        errors,
        source="analysis_stablecoin_total_market_cap",
        fn=lambda: soso.get_analysis_chart("stablecoin_total_market_cap", limit=7),
        fallback=[],
    )
    sector_spotlight = _call_with_capture(
        errors,
        source="sector_spotlight",
        fn=soso.get_sector_spotlight,
        fallback={},
    )

    assets: list[dict[str, Any]] = []
    for asset in CORE_ASSETS:
        row = currency_map.get(asset, {})
        currency_id = str(row.get("currency_id", ""))
        if not currency_id:
            continue
        snapshot = _call_with_capture(
            errors,
            source=f"{asset.lower()}_overview_snapshot",
            fn=lambda cid=currency_id: soso.get_currency_market_snapshot(cid),
            fallback={},
        )
        top_pairs = _call_with_capture(
            errors,
            source=f"{asset.lower()}_overview_pairs",
            fn=lambda cid=currency_id: soso.get_currency_pairs(cid, page_size=1),
            fallback=[],
        )
        assets.append(
            {
                "asset": asset,
                "currencyId": currency_id,
                "name": row.get("name"),
                "snapshot": _normalize_market_snapshot(asset, currency_id, snapshot) if snapshot else None,
                "leadPair": _normalize_pair(top_pairs[0]) if top_pairs else None,
            }
        )

    latest_fgi = _safe_float((fear_greed[0] if fear_greed else {}).get("crypto_fear_&_greed_index"))
    prev_fgi = _safe_float((fear_greed[1] if len(fear_greed) > 1 else {}).get("crypto_fear_&_greed_index"))
    latest_mcap = _safe_float((total_market_cap[0] if total_market_cap else {}).get("total_crypto_market_cap"))
    prev_mcap = _safe_float((total_market_cap[1] if len(total_market_cap) > 1 else {}).get("total_crypto_market_cap"))
    latest_stable = _safe_float((stablecoin_mcap[0] if stablecoin_mcap else {}).get("mcap"))
    prev_stable = _safe_float((stablecoin_mcap[1] if len(stablecoin_mcap) > 1 else {}).get("mcap"))

    sectors = sector_spotlight.get("sector", []) if isinstance(sector_spotlight, dict) else []
    spotlights = sector_spotlight.get("spotlight", []) if isinstance(sector_spotlight, dict) else []

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "marketPulse": {
            "fearGreed": {
                "latest": latest_fgi,
                "previous": prev_fgi,
                "delta": None if latest_fgi is None or prev_fgi is None else latest_fgi - prev_fgi,
                "series": fear_greed[:7],
            },
            "totalCryptoMarketCap": {
                "latest": latest_mcap,
                "dayChangePct": _pct_change(latest_mcap, prev_mcap),
                "series": total_market_cap[:7],
            },
            "stablecoinMarketCap": {
                "latest": latest_stable,
                "dayChangePct": _pct_change(latest_stable, prev_stable),
                "series": stablecoin_mcap[:7],
            },
        },
        "assetBoard": sorted(
            assets,
            key=lambda row: ((row.get("snapshot") or {}).get("marketCapRank") or 999999, row.get("asset", "")),
        ),
        "sectorRotation": {
            "leadersByChange": [
                {
                    "name": row.get("name"),
                    "changePct24h": _safe_float(row.get("24h_change_pct")),
                    "marketCapDominance": _safe_float(row.get("marketcap_dom")),
                }
                for row in _sorted_desc(sectors, "24h_change_pct")[:8]
            ],
            "spotlight": [
                {
                    "name": row.get("name"),
                    "changePct24h": _safe_float(row.get("24h_change_pct")),
                }
                for row in _sorted_desc(spotlights, "24h_change_pct")[:8]
            ],
        },
        "errors": errors,
    }


def _build_market_structure_payload(
    soso: SoSoValueTerminalClient,
    binance: BinanceTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    open_interest = _call_with_capture(
        errors,
        source="analysis_futures_open_interest",
        fn=lambda: soso.get_analysis_chart("futures_open_interest", limit=7),
        fallback=[],
    )
    funding = _call_with_capture(
        errors,
        source="analysis_funding_rate",
        fn=lambda: soso.get_analysis_chart("funding_rate", limit=7),
        fallback=[],
    )

    index_board: list[dict[str, Any]] = []
    for ticker in INDEX_TICKERS:
        snapshot = _call_with_capture(
            errors,
            source=f"index_{ticker}_snapshot",
            fn=lambda t=ticker: soso.get_index_market_snapshot(t),
            fallback={},
        )
        constituents = _call_with_capture(
            errors,
            source=f"index_{ticker}_constituents",
            fn=lambda t=ticker: soso.get_index_constituents(t),
            fallback=[],
        )
        index_board.append(_normalize_index_snapshot(ticker, snapshot, constituents))

    liquidity: dict[str, list[dict[str, Any]]] = {}
    for asset in HERO_ASSETS:
        currency_id = str(currency_map.get(asset, {}).get("currency_id", ""))
        liquidity[asset] = [
            _normalize_pair(row)
            for row in _call_with_capture(
                errors,
                source=f"{asset.lower()}_liquidity_pairs",
                fn=lambda cid=currency_id: soso.get_currency_pairs(cid, page_size=5),
                fallback=[],
            )[:5]
        ] if currency_id else []

    positioning = {
        asset: _normalize_positioning(
            _call_with_capture(
                errors,
                source=f"{asset.lower()}_market_structure_positioning",
                fn=lambda symbol=BINANCE_SYMBOL_BY_ASSET[asset]: binance.get_global_long_short_ratio(symbol, period="1d", limit=5),
                fallback=[],
            )
        )
        for asset in HERO_ASSETS
    }

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "futuresOpenInterest": open_interest[:7],
        "fundingRate": funding[:7],
        "indexLeadership": index_board,
        "liquidity": liquidity,
        "positioning": positioning,
        "errors": errors,
    }


def _build_news_payload(
    soso: SoSoValueTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    hot_news = _call_with_capture(
        errors,
        source="hot_news",
        fn=lambda: soso.get_hot_news(page_size=10),
        fallback=[],
    )
    research_news = _call_with_capture(
        errors,
        source="research_news",
        fn=lambda: soso.get_news(category="2,3", page_size=10),
        fallback=[],
    )

    asset_focus: dict[str, list[dict[str, Any]]] = {}
    for asset in HERO_ASSETS:
        currency_id = str(currency_map.get(asset, {}).get("currency_id", ""))
        asset_focus[asset] = [
            _normalize_news_item(row)
            for row in _call_with_capture(
                errors,
                source=f"{asset.lower()}_focus_news",
                fn=lambda cid=currency_id: soso.get_news(currency_id=cid, page_size=5),
                fallback=[],
            )[:5]
        ] if currency_id else []

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "hot": [_normalize_news_item(row, hot=True) for row in hot_news[:10]],
        "research": [_normalize_news_item(row) for row in research_news[:10]],
        "assetFocus": asset_focus,
        "errors": errors,
    }


def _build_macro_payload(
    soso: SoSoValueTerminalClient,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    calendar = _call_with_capture(
        errors,
        source="macro_events",
        fn=soso.get_macro_events,
        fallback=[],
    )
    history: dict[str, list[dict[str, Any]]] = {}

    top_events: list[str] = []
    for row in calendar[:3]:
        events = row.get("events", [])
        if isinstance(events, list):
            top_events.extend(str(event) for event in events[:2])

    for event_name in top_events[:4]:
        history[event_name] = _call_with_capture(
            errors,
            source=f"macro_history_{event_name}",
            fn=lambda name=event_name: soso.get_macro_event_history(name, limit=3),
            fallback=[],
        )

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "calendar": calendar,
        "eventHistory": history,
        "errors": errors,
    }


def _build_watchlist_payload(
    soso: SoSoValueTerminalClient,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    stock_rows = _call_with_capture(
        errors,
        source="crypto_stocks",
        fn=soso.get_crypto_stocks,
        fallback=[],
    )
    stock_map = {str(row.get("ticker", "")): row for row in stock_rows}
    stock_sectors = _call_with_capture(
        errors,
        source="crypto_stock_sectors",
        fn=soso.get_crypto_stock_sectors,
        fallback=[],
    )
    treasury_rows = _call_with_capture(
        errors,
        source="btc_treasuries",
        fn=soso.get_btc_treasuries,
        fallback=[],
    )
    treasury_map = {str(row.get("ticker", "")): row for row in treasury_rows}

    stocks: list[dict[str, Any]] = []
    for ticker in WATCHLIST_STOCKS:
        stock = stock_map.get(ticker)
        if not stock:
            continue
        snapshot = _call_with_capture(
            errors,
            source=f"crypto_stock_{ticker}",
            fn=lambda t=ticker: soso.get_crypto_stock_market_snapshot(t),
            fallback={},
        )
        stocks.append(_normalize_crypto_stock(stock, snapshot))

    treasuries: list[dict[str, Any]] = []
    for ticker in TREASURY_TICKERS:
        company = treasury_map.get(ticker)
        if not company:
            continue
        purchases = _call_with_capture(
            errors,
            source=f"btc_treasury_{ticker}",
            fn=lambda t=ticker: soso.get_btc_treasury_purchase_history(t, limit=3),
            fallback=[],
        )
        treasuries.append(_normalize_treasury_entry(company, purchases))

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "cryptoStocks": stocks,
        "stockSectors": [
            {
                "sectorName": row.get("sector_name"),
                "totalMarketCap": _safe_float(row.get("total_marketcap")),
                "changePct24h": _safe_float(row.get("change_pct_24h")),
            }
            for row in _sorted_desc(stock_sectors, "total_marketcap")[:8]
        ],
        "btcTreasuries": treasuries,
        "errors": errors,
    }


def _build_analysis_payload(
    soso: SoSoValueTerminalClient,
    currency_map: dict[str, dict[str, Any]],
    hero: dict[str, Any],
    overview: dict[str, Any],
    market_structure: dict[str, Any],
    macro: dict[str, Any],
    watchlist: dict[str, Any],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    macro_rows: list[dict[str, Any]] = []
    history = macro.get("eventHistory", {}) if isinstance(macro.get("eventHistory"), dict) else {}
    for day in (macro.get("calendar", []) or [])[:6]:
        for event_name in (day.get("events") or [])[:4]:
            event_history = history.get(event_name)
            if not event_history:
                event_history = _call_with_capture(
                    errors,
                    source=f"analysis_macro_history_{event_name}",
                    fn=lambda name=event_name: soso.get_macro_event_history(name, limit=5),
                    fallback=[],
                )
            latest = event_history[0] if event_history else {}
            actual = _safe_float(latest.get("actual"))
            forecast = _safe_float(latest.get("forecast"))
            previous = _safe_float(latest.get("previous"))
            macro_rows.append(
                {
                    "date": day.get("date"),
                    "event": event_name,
                    "actual": actual,
                    "forecast": forecast,
                    "previous": previous,
                    "surprise": _pct_change(actual, forecast),
                    "history": event_history[:5],
                }
            )

    flow_assets: list[dict[str, Any]] = []
    hero_assets = hero.get("assets", {}) if isinstance(hero.get("assets"), dict) else {}
    for asset in ["BTC", "ETH", "SOL", "XRP", "DOGE", "LINK", "AVAX"]:
        symbol = ETF_TYPE_BY_ASSET.get(asset, asset)
        history_rows = _call_with_capture(
            errors,
            source=f"analysis_etf_{asset}",
            fn=lambda s=symbol: soso.get_etf_summary_history(s, limit=10),
            fallback=[],
        )
        existing = ((hero_assets.get(asset) or {}).get("etf") or {}) if isinstance(hero_assets.get(asset), dict) else {}
        flow_assets.append(
            {
                "asset": asset,
                "dailyNetInflow": existing.get("dailyNetInflow") if existing else (_safe_float(history_rows[0].get("total_net_inflow")) if history_rows else None),
                "totalNetAssets": _safe_float(history_rows[0].get("total_net_assets")) if history_rows else None,
                "totalValueTraded": _safe_float(history_rows[0].get("total_value_traded")) if history_rows else None,
                "cumulativeNetInflow": _safe_float(history_rows[0].get("cum_net_inflow")) if history_rows else None,
                "history": _normalize_etf_history(history_rows[:10]),
            }
        )

    index_rows = market_structure.get("indexLeadership", []) if isinstance(market_structure.get("indexLeadership"), list) else []
    index_rotation = []
    for row in index_rows[:8]:
        ticker = row.get("ticker")
        constituents = _call_with_capture(
            errors,
            source=f"analysis_index_constituents_{ticker}",
            fn=lambda t=ticker: soso.get_index_constituents(str(t)),
            fallback=[],
        ) if ticker else []
        index_rotation.append(
            {
                **row,
                "topConstituents": [
                    {
                        "symbol": item.get("symbol"),
                        "weight": _safe_float(item.get("weight")),
                    }
                    for item in constituents[:5]
                    if isinstance(item, dict)
                ],
            }
        )

    unlock_supply = []
    for asset in ["SOL", "SUI", "AVAX", "LINK", "XRP"]:
        currency_id = str(currency_map.get(asset, {}).get("currency_id", ""))
        if not currency_id:
            continue
        economics = _call_with_capture(
            errors,
            source=f"token_economics_{asset}",
            fn=lambda cid=currency_id: soso.get_currency_token_economics(cid),
            fallback={},
        )
        supply = _call_with_capture(
            errors,
            source=f"supply_{asset}",
            fn=lambda cid=currency_id: soso.get_currency_supply(cid, limit=30),
            fallback=[],
        )
        unlock_supply.append(_normalize_token_economics(asset, economics, supply))

    crypto_stocks = watchlist.get("cryptoStocks", []) if isinstance(watchlist.get("cryptoStocks"), list) else []
    stock_sectors = watchlist.get("stockSectors", []) if isinstance(watchlist.get("stockSectors"), list) else []
    btc_treasuries = watchlist.get("btcTreasuries", []) if isinstance(watchlist.get("btcTreasuries"), list) else []

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "macroShock": {
            "events": macro_rows[:16],
        },
        "flowLens": {
            "assets": flow_assets,
        },
        "sectorRotation": {
            "indices": index_rotation,
            "spotlight": ((overview.get("sectorRotation") or {}).get("spotlight") or [])[:8],
        },
        "unlockSupply": {
            "assets": unlock_supply,
        },
        "cryptoStocksBridge": {
            "stocks": crypto_stocks,
            "sectors": stock_sectors,
            "btcTreasuries": btc_treasuries,
        },
        "errors": errors,
    }


def _build_desk_payload(
    hero: dict[str, Any],
    overview: dict[str, Any],
    market_structure: dict[str, Any],
    news: dict[str, Any],
    macro: dict[str, Any],
    watchlist: dict[str, Any],
) -> dict[str, Any]:
    assets = overview.get("assetBoard", []) if isinstance(overview.get("assetBoard"), list) else []
    hero_assets = hero.get("assets", {}) if isinstance(hero.get("assets"), dict) else {}
    pulse = overview.get("marketPulse", {}) if isinstance(overview.get("marketPulse"), dict) else {}
    structure_liquidity = market_structure.get("liquidity", {}) if isinstance(market_structure.get("liquidity"), dict) else {}
    sector_rotation = overview.get("sectorRotation", {}) if isinstance(overview.get("sectorRotation"), dict) else {}

    price_map: list[dict[str, Any]] = []
    for row in assets[:8]:
        snapshot = row.get("snapshot") or {}
        low = snapshot.get("low24h")
        high = snapshot.get("high24h")
        price = snapshot.get("price")
        range_position = None
        if all(value is not None for value in (low, high, price)) and high != low:
            range_position = max(0, min(1, (price - low) / (high - low)))
        price_map.append(
            {
                "asset": row.get("asset"),
                "price": price,
                "changePct24h": snapshot.get("changePct24h"),
                "turnover24h": snapshot.get("turnover24h"),
                "rangePosition24h": range_position,
                "low24h": low,
                "high24h": high,
                "downFromAth": snapshot.get("downFromAth"),
                "upFromCycleLow": snapshot.get("upFromCycleLow"),
            }
        )

    liquidity_rows: list[dict[str, Any]] = []
    for asset, pairs in structure_liquidity.items():
        for pair in (pairs or [])[:3]:
            up = pair.get("costToMoveUpUsd")
            down = pair.get("costToMoveDownUsd")
            imbalance = _pct_change(up, down) if up is not None and down is not None else None
            liquidity_rows.append(
                {
                    "asset": asset,
                    "market": pair.get("market"),
                    "pair": f"{pair.get('base')}/{pair.get('target')}",
                    "turnover24h": pair.get("turnover24h"),
                    "costToMoveUpUsd": up,
                    "costToMoveDownUsd": down,
                    "depthImbalancePct": imbalance,
                }
            )

    flow_rows: list[dict[str, Any]] = []
    for asset, bundle in hero_assets.items():
        etf = bundle.get("etf") or {}
        positioning = (bundle.get("positioning") or {}).get("latest") or {}
        flow_rows.append(
            {
                "asset": asset,
                "dailyNetInflow": etf.get("dailyNetInflow"),
                "history5d": etf.get("history5d", []),
                "longAccountShare": positioning.get("longAccountShare"),
                "shortAccountShare": positioning.get("shortAccountShare"),
                "longShortRatio": positioning.get("longShortRatio"),
            }
        )

    next_macro = []
    history = macro.get("eventHistory", {}) if isinstance(macro.get("eventHistory"), dict) else {}
    for day in (macro.get("calendar", []) or [])[:4]:
        events = []
        for event in (day.get("events") or [])[:3]:
            latest_history = (history.get(event) or [{}])[0]
            events.append(
                {
                    "name": event,
                    "actual": latest_history.get("actual"),
                    "forecast": latest_history.get("forecast"),
                    "previous": latest_history.get("previous"),
                }
            )
        next_macro.append({"date": day.get("date"), "events": events})

    stock_sectors = watchlist.get("stockSectors", []) if isinstance(watchlist.get("stockSectors"), list) else []

    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "pulse": {
            "fearGreed": pulse.get("fearGreed"),
            "totalCryptoMarketCap": pulse.get("totalCryptoMarketCap"),
            "stablecoinMarketCap": pulse.get("stablecoinMarketCap"),
        },
        "priceMap": price_map,
        "liquidityWatch": sorted(
            liquidity_rows,
            key=lambda row: _safe_float(row.get("turnover24h")) or 0,
            reverse=True,
        ),
        "flowWatch": flow_rows,
        "leverageWatch": {
            "futuresOpenInterest": market_structure.get("futuresOpenInterest", [])[:7],
            "fundingRate": market_structure.get("fundingRate", [])[:7],
            "positioning": market_structure.get("positioning", {}),
        },
        "rotationWatch": {
            "sectors": sector_rotation.get("leadersByChange", [])[:6],
            "spotlight": sector_rotation.get("spotlight", [])[:6],
            "indices": market_structure.get("indexLeadership", [])[:6],
            "cryptoStockSectors": stock_sectors[:6],
        },
        "catalysts": {
            "macro": next_macro,
            "news": (news.get("hot", []) or [])[:6],
        },
        "tradfiProxy": {
            "cryptoStocks": (watchlist.get("cryptoStocks", []) or [])[:6],
            "btcTreasuries": (watchlist.get("btcTreasuries", []) or [])[:5],
        },
        "errors": [],
    }


def _build_manifest(payload_files: list[str]) -> dict[str, Any]:
    return {
        "version": "v2",
        "generated_at": _utc_now(),
        "mode": "file_store",
        "payloads": {name.replace(".json", ""): name for name in payload_files},
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _payload_has_content(filename: str, payload: dict[str, Any]) -> bool:
    if filename == "news.json":
        asset_focus = payload.get("assetFocus")
        focus_count = 0
        if isinstance(asset_focus, dict):
            focus_count = sum(_list_count(rows) for rows in asset_focus.values())
        return _list_count(payload.get("hot")) + _list_count(payload.get("research")) + focus_count > 0

    if filename == "watchlist.json":
        return (
            _list_count(payload.get("cryptoStocks"))
            + _list_count(payload.get("stockSectors"))
            + _list_count(payload.get("btcTreasuries"))
            > 0
        )

    if filename == "desk.json":
        catalysts = payload.get("catalysts") if isinstance(payload.get("catalysts"), dict) else {}
        tradfi = payload.get("tradfiProxy") if isinstance(payload.get("tradfiProxy"), dict) else {}
        return (
            _list_count(catalysts.get("news"))
            + _list_count(catalysts.get("macro"))
            + _list_count(tradfi.get("cryptoStocks"))
            + _list_count(tradfi.get("btcTreasuries"))
            > 0
        )

    if filename == "analysis.json":
        bridge = payload.get("cryptoStocksBridge") if isinstance(payload.get("cryptoStocksBridge"), dict) else {}
        flow_lens = payload.get("flowLens") if isinstance(payload.get("flowLens"), dict) else {}
        return _list_count(bridge.get("stocks")) + _list_count(bridge.get("btcTreasuries")) + _list_count(flow_lens.get("assets")) > 0

    return True


def _write_json_preserving_existing(path: Path, payload: dict[str, Any]) -> bool:
    if not payload.get("errors") or _payload_has_content(path.name, payload):
        _write_json(path, payload)
        return False

    if not path.exists():
        _write_json(path, payload)
        return False

    try:
        existing = _read_json(path)
    except (OSError, json.JSONDecodeError):
        _write_json(path, payload)
        return False

    if _payload_has_content(path.name, existing):
        return True

    _write_json(path, payload)
    return False


def main() -> None:
    env = load_dotenv()
    soso = SoSoValueTerminalClient(env.get("SOSO_API_KEY", ""))
    binance = BinanceTerminalClient()

    shared_errors: list[dict[str, str]] = []
    currency_map = _build_currency_map(soso, shared_errors)

    hero = _build_hero_payload(soso, binance, currency_map, shared_errors.copy())
    overview = _build_overview_payload(soso, currency_map, shared_errors.copy())
    market_structure = _build_market_structure_payload(soso, binance, currency_map, shared_errors.copy())
    news = _build_news_payload(soso, currency_map, shared_errors.copy())
    macro = _build_macro_payload(soso, shared_errors.copy())
    watchlist = _build_watchlist_payload(soso, shared_errors.copy())
    analysis = _build_analysis_payload(
        soso,
        currency_map,
        hero,
        overview,
        market_structure,
        macro,
        watchlist,
        shared_errors.copy(),
    )
    desk = _build_desk_payload(hero, overview, market_structure, news, macro, watchlist)

    payloads = {
        "hero.json": hero,
        "overview.json": overview,
        "desk.json": desk,
        "market_structure.json": market_structure,
        "news.json": news,
        "macro.json": macro,
        "watchlist.json": watchlist,
        "analysis.json": analysis,
    }
    manifest = _build_manifest(list(payloads.keys()))
    payloads["manifest.json"] = manifest

    preserved: list[str] = []
    for filename, payload in payloads.items():
        if _write_json_preserving_existing(WEBSITE_DATA_DIR / filename, payload):
            preserved.append(filename)

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(WEBSITE_DATA_DIR),
                "files": list(payloads.keys()),
                "preserved_existing": preserved,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
