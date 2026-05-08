# Website Data

This folder stores local development payloads for the Narralytica market context terminal.

## Purpose

`scripts/` writes JSON payloads here before they are optionally published to Supabase.

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

- This is generated runtime output.
- The JSON files in `terminal/` are ignored by git.
- Supabase is the deployment delivery path for the website.
