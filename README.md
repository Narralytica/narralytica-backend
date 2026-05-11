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
- optional Supabase publishing through `scripts/publish_terminal_payloads.py`


## End-to-End Flow

```text
SoSoValue API + Binance + xAI
        ↓
scripts/build_website_data.py
        ↓
website_data/terminal/*.json
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
SOSO_API_KEY=your_sosovalue_api_key
XAI_API=your_xai_api_key
XAI_MODEL=grok-4.20-reasoning
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
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

## Wave 1 Demo Notes

- This is a working market-context prototype.
- The backend generates structured JSON payloads used by the website.
- Some sections may use fallback or demo-safe handling when API data is unavailable.
- The goal is to prove the data pipeline and user value, not to provide trading signals.

## Known Limitations / Next Steps

- Provider availability can affect freshness and completeness.
- The desk brief depends on the latest generated `desk.json`.
- Fetching currently runs locally by design. Wave 2 will move the pipeline toward a server-side scheduled runtime after more backend depth is added.
- Supabase is used as a delivery store when publishing is enabled; the backend still performs the fetching and calculations.
- The earlier decision/signal engine is held for Wave 2 because the backtesting and refinement layers still need correction before being exposed.
- The project is in Wave 1 demo scope, so payload schemas may still evolve.
