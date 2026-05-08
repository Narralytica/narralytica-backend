from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

import _bootstrap
from narralytica.config import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TERMINAL_DATA_DIR = PROJECT_ROOT / "website_data" / "terminal"
DESK_DATA_PATH = TERMINAL_DATA_DIR / "desk.json"
BRIEF_PATH = TERMINAL_DATA_DIR / "desk_brief.json"
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"


DESK_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "valid_for_date": {"type": "string"},
        "headline": {"type": "string"},
        "subheadline": {"type": "string"},
        "market_stance": {"type": "string", "enum": ["risk_on", "risk_off", "mixed", "fragile"]},
        "whats_new": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tone": {"type": "string", "enum": ["green", "amber", "red"]},
                    "text": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["tone", "text", "source"],
            },
        },
        "trade_setup": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "analysis": {"type": "string"},
                "watchlist": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "symbol": {"type": "string"},
                            "reason": {"type": "string"},
                            "watch_for": {"type": "string"},
                            "risk": {"type": "string"},
                        },
                        "required": ["symbol", "reason", "watch_for", "risk"],
                    },
                },
            },
            "required": ["title", "analysis", "watchlist"],
        },
        "week_ahead": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "date": {"type": "string"},
                    "label": {"type": "string"},
                    "detail": {"type": "string"},
                    "importance": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["date", "label", "detail", "importance"],
            },
        },
        "key_data": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["label", "value", "context"],
            },
        },
        "risk_notes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "valid_for_date",
        "headline",
        "subheadline",
        "market_stance",
        "whats_new",
        "trade_setup",
        "week_ahead",
        "key_data",
        "risk_notes",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _existing_is_fresh(path: Path, valid_for_date: str) -> bool:
    if not path.exists():
        return False
    try:
        existing = _read_json(path)
    except Exception:
        return False
    return existing.get("valid_for_date") == valid_for_date


def _compact_for_prompt(desk: dict[str, Any]) -> dict[str, Any]:
    return {
        "pulse": desk.get("pulse"),
        "priceMap": (desk.get("priceMap") or [])[:8],
        "liquidityWatch": (desk.get("liquidityWatch") or [])[:8],
        "flowWatch": desk.get("flowWatch"),
        "leverageWatch": {
            "futuresOpenInterest": (desk.get("leverageWatch") or {}).get("futuresOpenInterest", [])[:5],
            "fundingRate": (desk.get("leverageWatch") or {}).get("fundingRate", [])[:5],
            "positioning": (desk.get("leverageWatch") or {}).get("positioning", {}),
        },
        "rotationWatch": {
            "sectors": ((desk.get("rotationWatch") or {}).get("sectors") or [])[:6],
            "indices": ((desk.get("rotationWatch") or {}).get("indices") or [])[:6],
            "cryptoStockSectors": ((desk.get("rotationWatch") or {}).get("cryptoStockSectors") or [])[:6],
        },
        "catalysts": {
            "macro": ((desk.get("catalysts") or {}).get("macro") or [])[:5],
            "news": ((desk.get("catalysts") or {}).get("news") or [])[:6],
        },
        "tradfiProxy": desk.get("tradfiProxy"),
    }


def _call_xai(api_key: str, model: str, desk: dict[str, Any], valid_for_date: str) -> dict[str, Any]:
    system_prompt = (
        "You are a crypto macro trading desk analyst. Use only the provided structured market data. "
        "Do not invent prices, events, sources, or tickers. Do not give financial advice or trade instructions. "
        "Produce concise trader-facing context: what changed, what to watch, which tokens deserve attention, and why. "
        "Use actual data references in source fields such as SoSoValue news, macro, ETF flow, funding, liquidity, sector rotation."
    )
    user_prompt = {
        "task": "Create today's Narralytica market desk brief.",
        "valid_for_date": valid_for_date,
        "style": "Dense, trader-facing, monochrome terminal copy. No hype. No scoring. No rankings.",
        "constraints": [
            "watchlist should include 3 to 6 symbols from provided data only",
            "whats_new should include 4 concise bullets",
            "week_ahead should include upcoming macro/catalyst items from provided data",
            "key_data should include 4 to 6 data points",
            "risk_notes should include 2 to 4 concise risks",
        ],
        "data": _compact_for_prompt(desk),
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, separators=(",", ":"))},
        ],
        "temperature": 0.2,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "narralytica_desk_brief",
                "strict": True,
                "schema": DESK_BRIEF_SCHEMA,
            },
        },
    }
    req = request.Request(
        XAI_BASE_URL,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(body).encode("utf-8"),
    )
    with request.urlopen(req, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))

    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed["generated_at"] = _utc_now()
    parsed["model"] = model
    parsed["source_payload_generated_at"] = desk.get("generated_at")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily xAI desk brief from terminal desk data.")
    parser.add_argument("--force", action="store_true", help="Regenerate even if today's brief already exists.")
    args = parser.parse_args()

    valid_for_date = _today()
    if not args.force and _existing_is_fresh(BRIEF_PATH, valid_for_date):
        print(json.dumps({"ok": True, "skipped": True, "path": str(BRIEF_PATH)}, indent=2))
        return

    env = load_dotenv()
    api_key = env.get("XAI_API") or env.get("XAI_API_KEY")
    if not api_key:
        raise RuntimeError("XAI_API is required in .env")

    model = env.get("XAI_MODEL", "grok-4.20-reasoning")
    desk = _read_json(DESK_DATA_PATH)
    brief = _call_xai(api_key, model, desk, valid_for_date)
    _write_json(BRIEF_PATH, brief)
    print(json.dumps({"ok": True, "skipped": False, "path": str(BRIEF_PATH), "model": model}, indent=2))


if __name__ == "__main__":
    main()
