# Website Data

This folder stores generated payloads for the Narralytica market context terminal.

## Purpose

`scripts/` writes terminal JSON payloads here after fetching and normalizing market data.

These files are the local output of the backend pipeline. When publishing is enabled, the same payloads are uploaded to Supabase for the live website.

## Current Structure

- `terminal/manifest.json`  
  Declares file version, refresh timing, and available payload files.

- `terminal/hero.json`  
  Hero/header payload for the market context terminal.

- `terminal/overview.json`  
  Core market pulse, sector rotation, and asset board payload.

- `terminal/desk.json`  
  Aggregated market desk context used by the daily desk brief.

- `terminal/desk_brief.json`  
  xAI-generated daily desk brief based on `desk.json`.

- `terminal/market_structure.json`  
  Futures positioning, funding, liquidity, and index leadership payload.

- `terminal/news.json`  
  Hot, research, and asset-focus news payload.

- `terminal/macro.json`  
  Macro calendar and event-history payload.

- `terminal/watchlist.json`  
  Crypto stock, BTC treasury, and related watchlist payload.

- `terminal/analysis.json`  
  Structured analysis payload combining market, flow, macro, and token context.

## Notes

- This folder contains generated runtime output.
- The JSON files in `terminal/` are ignored by git.
- Do not edit generated JSON files by hand.
- To refresh the payloads, run the backend pipeline from the repository root.