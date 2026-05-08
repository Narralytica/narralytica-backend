# Narralytica Terminal Supabase Setup

This is the clean Supabase setup for the current Narralytica market context terminal.

It does not depend on the old signal-engine Supabase tables.

## 1. Create The Table

Run this file in the Supabase SQL editor:

```text
supabase/terminal_schema.sql
```

It creates one public-read table:

```text
public.terminal_payloads
```

## 2. Required Environment

Add these to `.env` in the backend root:

```env
SOSO_API_KEY=your_sosovalue_api_key
XAI_API=your_xai_api_key
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

`SUPABASE_SERVICE_ROLE_KEY` is used only by the backend publisher.

## 3. Build Payloads

```bash
python scripts2/build_website_data.py
```

Optional daily AI brief:

```bash
python scripts2/generate_desk_brief.py --force
```

## 4. Publish To Supabase

Dry run:

```bash
python scripts2/publish_terminal_payloads.py --dry-run
```

Write to Supabase:

```bash
python scripts2/publish_terminal_payloads.py
```

Full pipeline:

```bash
python scripts2/run_terminal_pipeline.py --publish
```

## 5. Payload Rows

The publisher upserts these ten rows:

```text
terminal:manifest
terminal:hero
terminal:overview
terminal:desk
terminal:desk_brief
terminal:market_structure
terminal:news
terminal:macro
terminal:watchlist
terminal:analysis
```

Each row contains:

- `payload_key`
- `payload`
- `version`
- `generated_at`
- `published_at`
- `source`
- `refresh_interval_minutes`
- `payload_hash`
- `updated_at`

## 6. Website Endpoint Count

The whole website can use one Supabase table endpoint:

```text
/rest/v1/terminal_payloads
```

Recommended query:

```text
/rest/v1/terminal_payloads?payload_key=in.(terminal:manifest,terminal:hero,terminal:overview,terminal:desk,terminal:desk_brief,terminal:market_structure,terminal:news,terminal:macro,terminal:watchlist,terminal:analysis)&select=payload_key,payload,generated_at,published_at,payload_hash
```

If you keep the Next.js `/api/terminal-data` route, the browser still calls one website endpoint, and that route can call this one Supabase endpoint server-side.
