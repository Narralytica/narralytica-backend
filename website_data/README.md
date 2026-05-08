# Website Data

This folder is the temporary file-based data source for the Narralytica website while we move away from the legacy signal backend and before we switch the new market-context backend to Supabase.

## Purpose

`scripts2/` writes JSON payloads here.

The website should eventually read from these files instead of relying on the old signal tables and caches.

## Current structure

- `terminal/manifest.json`
  Declares file version, refresh timing, and available payload files.
- `terminal/hero.json`
  Hero/header payload for the market context terminal.
- `terminal/overview.json`
  Core market pulse, sector rotation, and asset board payload.
- `terminal/market_structure.json`
  Futures positioning, funding, liquidity, and index leadership payload.
- `terminal/news.json`
  Hot, research, and asset-focus news payload.
- `terminal/macro.json`
  Macro calendar and event-history payload.
- `terminal/watchlist.json`
  Crypto stock, BTC treasury, and related watchlist payload.

## Notes

- This is a transport layer only.
- Later we can move the same payload shapes into Supabase with minimal frontend churn.
