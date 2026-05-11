# Narralytica Backend

Narralytica is a crypto market context and analysis terminal. This backend turns scattered market data into structured JSON payloads that power the Narralytica website.

It is not a buy/sell signal generator, trading bot, or financial advice system.

## What This Backend Does

- Fetches market context from SoSoValue, Binance, and xAI.
- Normalizes ETF flows, market structure, sectors, macro/news, watchlists, and desk context.
- Builds JSON payloads for the website terminal.
- Optionally generates an xAI-powered daily desk brief from the latest payloads.
- Publishes generated payloads to Supabase storage when requested.

The core user value is context: the backend helps the website explain what is moving, why it may be moving, and which market inputs are worth watching next.

## Active Direction

The active backend path is:

- `scripts/`
- `website_data/terminal/`
- `supabase/terminal_schema.sql`

The Python scripts are the backend engine. They fetch market data, normalize it, generate terminal JSON payloads, and optionally generate the daily desk brief.

Supabase is used as the hosted payload store for the live website. The backend publishes generated payloads into Supabase, and the website reads them from there.

## End-to-End Flow

```text
SoSoValue API + Binance + xAI
        ↓
scripts/build_website_data.py
        ↓
website_data/terminal/*.json
        ↓
scripts/publish_terminal_payloads.py
        ↓
Supabase terminal_payloads table
        ↓
Next.js /api/terminal-data
        ↓
Narralytica dashboard
```

## SoSoValue API Integration Map

| Website Section | SoSoValue Data Used | Output |
| --- | --- | --- |
| ETF Flow | BTC/ETH ETF flow data | ETF inflow/outflow trend cards |
| Sector Rotation | SoSoValue sector/index data | Top sectors and market structure context |
| News / Events | SoSoValue macro and hot news | Market catalyst feed |
| Desk Brief | SoSoValue news + market context | Daily market intelligence brief |
| Analysis | Market, token, flow, and macro inputs | Structured research context |

## APIs Used

| API / Endpoint | Used For | Output In Narralytica |
| --- | --- | --- |
| `GET https://api.sosovalue.xyz/openapi/v1/currencies` | Currency universe and IDs | Maps assets such as BTC/ETH/SOL to SoSoValue currency records |
| `GET /currencies/{currency_id}/market-snapshot` | Price, market cap, volume, and daily movement | Terminal overview, ticker tape, pulse, and desk context |
| `GET /currencies/{currency_id}/klines?interval=1d&limit=7` | Recent spot market path | Overview trend context and short history cards |
| `GET /currencies/{currency_id}/pairs?page=1&page_size=5` | Trading pairs, turnover, and liquidity context | Liquidity map and market structure views |
| `GET /currencies/{currency_id}/token-economics` | Token economics metadata | Analysis payloads and token context where available |
| `GET /currencies/{currency_id}/supply?limit=30` | Supply history | Supply/unlock analysis inputs |
| `GET /currencies/{currency_id}/fundraising` | Fundraising and allocation context | Unlock/supply and token pressure context |
| `GET /currencies/sector-spotlight` | Sector-level market spotlight | Sector rotation and market structure context |
| `GET /etfs/summary-history?symbol={BTC_or_ETH}&country_code=US&limit=5` | BTC/ETH ETF net flow history | ETF flow cards and flow lens |
| `GET /etfs?symbol={BTC_or_ETH}&country_code=US` | ETF product list | ETF market context and asset coverage |
| `GET /etfs/{ticker}/market-snapshot` | ETF snapshot data | ETF flow and market snapshot details |
| `GET /analyses` | Available SoSoValue analysis charts | Analysis payload discovery |
| `GET /analyses/funding_rate?limit=7` | Funding-rate analysis chart | Futures/perp bias context |
| `GET /indices` | SoSoValue index list | Index and sector coverage |
| `GET /indices/{ticker}/market-snapshot` | Index performance and market data | SoSoValue indices and sector rotation cards |
| `GET /indices/{ticker}/constituents` | Index constituents and weights | Index constituents and narrative weights |
| `GET /news?page=1&page_size=20&language=en` | General news feed | Events and desk context |
| `GET /news/hot?page=1&page_size=10&language=en` | Hot market news | Hot news feed and desk brief inputs |
| `GET /macro/events` | Macro calendar | Upcoming catalysts and events section |
| `GET /macro/events/{event_name}/history?limit=3` | Historical macro actual/forecast/previous values | Macro surprise tracker |
| `GET /crypto-stocks` | Crypto-linked public equities | Equity proxy board |
| `GET /crypto-stocks/{ticker}/market-snapshot` | Equity proxy price and turnover | TradFi proxy and watch boards |
| `GET /crypto-stocks/sectors` | Crypto-stock sector groups | Equity sector read-through |
| `GET /crypto-stocks/sector/{sector_name}/index?limit=7` | Sector index history | Crypto-stock bridge context |
| `GET /btc-treasuries` | Corporate BTC treasury holdings | BTC treasury board |
| `GET /btc-treasuries/{ticker}/purchase-history?limit=5` | Recent BTC treasury purchases | Treasury activity rows |
| `GET https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=1d&limit=5` | Binance futures long/short account ratio | Longs vs shorts and positioning context |
| `POST https://api.x.ai/v1/chat/completions` | xAI desk brief generation | Daily desk brief from prepared market context |

## How To Run Locally

Run from the backend repository root.

Build terminal payloads:

```bash
python scripts/build_website_data.py
```

Generate or refresh the daily desk brief:

```bash
python scripts/generate_desk_brief.py --force
```

Run the full local pipeline:

```bash
python scripts/run_terminal_pipeline.py
```

Run the full pipeline and publish to Supabase:

```bash
python scripts/run_terminal_pipeline.py --publish
```

Dry-run Supabase publishing:

```bash
python scripts/run_terminal_pipeline.py --dry-run-publish
```

## Environment Variables

Create a local `.env` file in the backend repo.

```env
SOSO_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
XAI_API=
```

Notes:

- `SOSO_API_KEY` is required for SoSoValue-powered payloads.
- Binance public endpoints are used without a key in the current scripts.
- `XAI_API` is required only when generating the desk brief.
- Supabase variables are required only when publishing payloads.

## Generated Output

The active output folder is:

```text
website_data/terminal/
```

Generated payloads include:

- `manifest.json`
- `hero.json`
- `overview.json`
- `desk.json`
- `desk_brief.json`
- `market_structure.json`
- `news.json`
- `macro.json`
- `watchlist.json`
- `analysis.json`

These files are generated artifacts for the website and should not be edited by hand as source data.

## Supabase Delivery Store

Supabase is used as a delivery layer for the live website.

The backend publishes each generated payload into the `terminal_payloads` table as one row per payload:

- `terminal:manifest`
- `terminal:hero`
- `terminal:overview`
- `terminal:desk`
- `terminal:desk_brief`
- `terminal:market_structure`
- `terminal:news`
- `terminal:macro`
- `terminal:watchlist`
- `terminal:analysis`

The website reads these rows through its `/api/terminal-data` route.

Supabase does not contain the main backend logic. The backend logic lives in the Python scripts.

## Wave 1 Demo Scope

- This is a working market-context prototype.
- The backend collects market data, structures it, and prepares payloads for the website.
- The website displays those payloads as a market intelligence terminal.
- The goal is to prove the data pipeline and user value, not to provide trading signals.
- Some sections may use fallback or demo-safe handling when provider data is unavailable.

## Known Limitations / Next Steps

- Provider availability can affect freshness and completeness.
- The desk brief depends on the latest generated `desk.json`.
- Fetching currently runs from the Python pipeline. A later version can move this toward a scheduled server-side runtime.
- Payload schemas may evolve as the terminal gains richer drilldowns and clearer source transparency.
- Future versions may add backtested research tools, saved watchlists, alerts, and historical market-reaction analysis.