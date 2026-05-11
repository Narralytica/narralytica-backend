# scripts

Active backend scripts for the Narralytica market context terminal.

It builds structured market context for the website: market pulse, ETF flow, liquidity, macro events, news, crypto-stock bridges, BTC treasury data, and the daily desk brief.

## Files

- `config.py`
  Minimal local `.env` loader used by the scripts.
- `soso_client.py`
  Standard-library API clients for SoSoValue and Binance.
- `build_website_data.py`
  Main data builder. Fetches market context and writes JSON payloads to `website_data/terminal/`.
- `generate_desk_brief.py`
  Uses `XAI_API` once per day, or with `--force`, to generate `desk_brief.json` from `desk.json`.
- `publish_terminal_payloads.py`
  Publishes generated terminal payloads into the new Supabase `terminal_payloads` table.
- `run_terminal_pipeline.py`
  Runs the builder, optional desk brief refresh, and optional Supabase publish in sequence.

## Usage

From the backend root:

```bash
python scripts/build_website_data.py
```

Then optionally:

```bash
python scripts/generate_desk_brief.py --force
```

Publish payloads to Supabase:

```bash
python scripts/publish_terminal_payloads.py
```

Preview the publish without writing:

```bash
python scripts/publish_terminal_payloads.py --dry-run
```

Run the full production-style pipeline:

```bash
python scripts/run_terminal_pipeline.py --publish
```

## Output

The website consumes these files through `/api/terminal-data`:

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

## Design Contract

The payloads should provide actual market context:

- raw values
- histories
- flows
- event timing
- positioning
- sector and index structure

Do not add generated trade calls here. The frontend should present context and analysis tools.

## Supabase Publishing

Supabase is used as the hosted payload store for the live website.

`publish_terminal_payloads.py` uploads the generated JSON payloads from `website_data/terminal/` into the `terminal_payloads` table.

The backend logic still lives in the Python scripts. Supabase only stores the final payloads so the website can read them through `/api/terminal-data`.

Run `supabase/terminal_schema.sql` in the Supabase SQL editor for a clean terminal-only setup.

Payloads are upserted into `public.terminal_payloads` as one row per terminal payload:

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

The website loads terminal data through its `/api/terminal-data` route, which reads these rows from Supabase by filtering `payload_key`.