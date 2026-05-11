from __future__ import annotations

from typing import Any
from urllib import parse, request
import json
import time


def _fetch_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout: int = 20,
) -> Any:
    final_url = url
    if params:
        query = parse.urlencode({key: value for key, value in params.items() if value is not None})
        if query:
            final_url = f"{url}?{query}"

    data: bytes | None = None
    final_headers = {
        "Accept": "application/json",
        "User-Agent": "NarralyticaTerminal/1.0 (+https://narralytica.local)",
    }
    if headers:
        final_headers.update(headers)

    if body is not None:
        final_headers.setdefault("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")

    req = request.Request(final_url, method=method, headers=final_headers, data=data)
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _unwrap_data(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    code = payload.get("code")
    if code not in (None, 0):
        message = payload.get("message") or payload.get("msg") or "Unknown SoSoValue error"
        raise RuntimeError(f"SoSoValue API error {code}: {message}")

    if "data" in payload:
        return payload.get("data")
    return payload


class SoSoValueTerminalClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("SOSO_API_KEY is required")
        self.base_url = "https://api.sosovalue.xyz/openapi/v1"
        self.api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-soso-api-key": self.api_key}

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        payload = _fetch_json(
            f"{self.base_url}{path}",
            headers=self._headers,
            params=params,
        )
        return _unwrap_data(payload)

    def get_currencies(self) -> list[dict[str, Any]]:
        data = self._get("/currencies")
        return data if isinstance(data, list) else []

    def get_currency_market_snapshot(self, currency_id: str) -> dict[str, Any]:
        data = self._get(f"/currencies/{currency_id}/market-snapshot")
        return data if isinstance(data, dict) else {}

    def get_currency_token_economics(self, currency_id: str) -> dict[str, Any]:
        data = self._get(f"/currencies/{currency_id}/token-economics")
        return data if isinstance(data, dict) else {}

    def get_currency_supply(self, currency_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
        data = self._get(f"/currencies/{currency_id}/supply", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_currency_fundraising(self, currency_id: str) -> dict[str, Any] | list[dict[str, Any]]:
        data = self._get(f"/currencies/{currency_id}/fundraising")
        return data if isinstance(data, (dict, list)) else {}

    def get_currency_pairs(
        self,
        currency_id: str,
        *,
        page: int = 1,
        page_size: int = 5,
    ) -> list[dict[str, Any]]:
        data = self._get(
            f"/currencies/{currency_id}/pairs",
            params={"page": page, "page_size": page_size},
        )
        if isinstance(data, dict):
            rows = data.get("list", [])
            return rows if isinstance(rows, list) else []
        return []

    def get_currency_klines(
        self,
        currency_id: str,
        *,
        interval: str = "1d",
        limit: int = 7,
    ) -> list[dict[str, Any]]:
        data = self._get(
            f"/currencies/{currency_id}/klines",
            params={"interval": interval, "limit": limit},
        )
        return data if isinstance(data, list) else []

    def get_sector_spotlight(self) -> dict[str, Any]:
        data = self._get("/currencies/sector-spotlight")
        return data if isinstance(data, dict) else {}

    def get_etf_summary_history(
        self,
        symbol: str,
        *,
        country_code: str = "US",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        data = self._get(
            "/etfs/summary-history",
            params={"symbol": symbol, "country_code": country_code, "limit": limit},
        )
        return data if isinstance(data, list) else []

    def get_etf_list(self, symbol: str, *, country_code: str = "US") -> list[dict[str, Any]]:
        data = self._get("/etfs", params={"symbol": symbol, "country_code": country_code})
        return data if isinstance(data, list) else []

    def get_etf_market_snapshot(self, ticker: str) -> dict[str, Any]:
        data = self._get(f"/etfs/{ticker}/market-snapshot")
        return data if isinstance(data, dict) else {}

    def get_analyses(self) -> list[dict[str, Any]]:
        data = self._get("/analyses")
        return data if isinstance(data, list) else []

    def get_analysis_chart(self, chart_name: str, *, limit: int = 7) -> list[dict[str, Any]]:
        data = self._get(f"/analyses/{chart_name}", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_indices(self) -> list[str]:
        data = self._get("/indices")
        return data if isinstance(data, list) else []

    def get_index_market_snapshot(self, ticker: str) -> dict[str, Any]:
        data = self._get(f"/indices/{ticker}/market-snapshot")
        return data if isinstance(data, dict) else {}

    def get_index_constituents(self, ticker: str) -> list[dict[str, Any]]:
        data = self._get(f"/indices/{ticker}/constituents")
        return data if isinstance(data, list) else []

    def get_news(
        self,
        *,
        category: str | None = None,
        currency_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        data = self._get(
            "/news",
            params={
                "category": category,
                "currency_id": currency_id,
                "page": page,
                "page_size": page_size,
                "language": language,
            },
        )
        if isinstance(data, dict):
            rows = data.get("list", [])
            return rows if isinstance(rows, list) else []
        return []

    def get_hot_news(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        data = self._get(
            "/news/hot",
            params={"page": page, "page_size": page_size, "language": language},
        )
        if isinstance(data, dict):
            rows = data.get("list", [])
            return rows if isinstance(rows, list) else []
        return []

    def get_macro_events(self) -> list[dict[str, Any]]:
        data = self._get("/macro/events")
        return data if isinstance(data, list) else []

    def get_macro_event_history(self, event_name: str, *, limit: int = 3) -> list[dict[str, Any]]:
        encoded = parse.quote(event_name, safe="")
        data = self._get(f"/macro/events/{encoded}/history", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_crypto_stocks(self) -> list[dict[str, Any]]:
        data = self._get("/crypto-stocks")
        return data if isinstance(data, list) else []

    def get_crypto_stock_market_snapshot(self, ticker: str) -> dict[str, Any]:
        data = self._get(f"/crypto-stocks/{ticker}/market-snapshot")
        return data if isinstance(data, dict) else {}

    def get_crypto_stock_sectors(self) -> list[dict[str, Any]]:
        data = self._get("/crypto-stocks/sectors")
        return data if isinstance(data, list) else []

    def get_crypto_stock_sector_index(self, sector_name: str, *, limit: int = 7) -> list[dict[str, Any]]:
        encoded = parse.quote(sector_name, safe="")
        data = self._get(f"/crypto-stocks/sector/{encoded}/index", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_btc_treasuries(self) -> list[dict[str, Any]]:
        data = self._get("/btc-treasuries")
        return data if isinstance(data, list) else []

    def get_btc_treasury_purchase_history(self, ticker: str, *, limit: int = 5) -> list[dict[str, Any]]:
        data = self._get(f"/btc-treasuries/{ticker}/purchase-history", params={"limit": limit})
        return data if isinstance(data, list) else []


class BinanceTerminalClient:
    def __init__(self) -> None:
        self.base_url = "https://fapi.binance.com"

    def get_global_long_short_ratio(
        self,
        symbol: str,
        *,
        period: str = "1d",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                payload = _fetch_json(
                    f"{self.base_url}/futures/data/globalLongShortAccountRatio",
                    params={
                        "symbol": symbol,
                        "period": period,
                        "limit": limit,
                    },
                    timeout=30,
                )
                return payload if isinstance(payload, list) else []
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        if last_error:
            raise last_error
        return []
