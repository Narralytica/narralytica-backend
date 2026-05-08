from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from config import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TERMINAL_DATA_DIR = PROJECT_ROOT / "website_data" / "terminal"

TERMINAL_PAYLOADS = [
    "manifest",
    "hero",
    "overview",
    "desk",
    "desk_brief",
    "market_structure",
    "news",
    "macro",
    "watchlist",
    "analysis",
]

REFRESH_INTERVAL_BY_PAYLOAD = {
    "manifest": 15,
    "hero": 5,
    "overview": 5,
    "desk": 5,
    "desk_brief": 1440,
    "market_structure": 5,
    "news": 5,
    "macro": 60,
    "watchlist": 30,
    "analysis": 15,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_key(name: str) -> str:
    return f"terminal:{name}"


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _generated_at(payload: dict[str, Any]) -> str | None:
    value = payload.get("generated_at")
    if isinstance(value, str) and value:
        return value
    valid_for_date = payload.get("valid_for_date")
    if isinstance(valid_for_date, str) and valid_for_date:
        return f"{valid_for_date}T00:00:00+00:00"
    return None


def _build_rows(payload_names: list[str]) -> list[dict[str, Any]]:
    published_at = _utc_now()
    rows: list[dict[str, Any]] = []

    for name in payload_names:
        path = TERMINAL_DATA_DIR / f"{name}.json"
        payload = _read_json(path)
        rows.append(
            {
                "payload_key": _payload_key(name),
                "payload": payload,
                "version": str(payload.get("version", "v2")),
                "generated_at": _generated_at(payload),
                "published_at": published_at,
                "source": f"scripts/{path.name}",
                "refresh_interval_minutes": REFRESH_INTERVAL_BY_PAYLOAD.get(name, 15),
                "payload_hash": _payload_hash(payload),
                "updated_at": published_at,
            }
        )

    return rows


def _supabase_upsert(*, supabase_url: str, service_role_key: str, rows: list[dict[str, Any]]) -> None:
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is required")
    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")

    query = parse.urlencode({"on_conflict": "payload_key"})
    url = f"{supabase_url.rstrip('/')}/rest/v1/terminal_payloads?{query}"
    req = request.Request(
        url,
        method="POST",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=merge-duplicates",
        },
        data=json.dumps(rows).encode("utf-8"),
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase upsert failed with HTTP {exc.code}: {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish terminal JSON payloads into the new Supabase terminal_payloads table.")
    parser.add_argument(
        "--payload",
        action="append",
        choices=TERMINAL_PAYLOADS,
        help="Publish only this payload. Can be passed multiple times. Defaults to all terminal payloads.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate files and print what would be published.")
    args = parser.parse_args()

    payload_names = args.payload or TERMINAL_PAYLOADS
    rows = _build_rows(payload_names)

    if not args.dry_run:
        env = load_dotenv(PROJECT_ROOT / ".env")
        _supabase_upsert(
            supabase_url=env.get("SUPABASE_URL", ""),
            service_role_key=env.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            rows=rows,
        )

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "table": "terminal_payloads",
                "rows": [
                    {
                        "payload_key": row["payload_key"],
                        "generated_at": row["generated_at"],
                        "refresh_interval_minutes": row["refresh_interval_minutes"],
                        "payload_hash": row["payload_hash"],
                    }
                    for row in rows
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
