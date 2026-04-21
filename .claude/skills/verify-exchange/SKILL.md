---
name: verify-exchange
description: Verify a scaffolded exchange connector actually streams the four required leg fields (mark_price, funding_rate, funding_interval_h, next_funding_time) before committing. Use after /add-exchange or any connector edit.
---

# Verifying an exchange connector

Companion skill to `/add-exchange`. Scaffolding a connector is one thing;
confirming it streams the four fields on real ticks is the step that
catches the silent footguns (cache not wired, wrong fundingRate field,
missing User-Agent). **Do not commit until this passes.**

## Run it

```bash
cd backend && ./venv/bin/python -m scripts.verify_exchange <exchange_id>
# e.g.
./venv/bin/python -m scripts.verify_exchange okx --seconds 60
```

Default window is 60s. Bump to 90 for REST-poll archetypes (MEXC,
Hyperliquid) that fire funding lazily, or if the sample symbol's
funding hasn't settled recently.

## What it checks

The helper in `backend/scripts/verify_exchange.py`:

1. **Reads `EXCHANGES[<id>]` metadata** and echoes `fee_source_url`,
   `maker_fee`, `taker_fee`, `default_funding_interval_h`. If
   `fee_source_url` is missing or non-http, the backend won't boot at
   all — that's the `ExchangeWS.__init_subclass__` gate from
   `backend/exchange/base.py`.
2. **Runs discovery once** and reports perp count + elapsed. Discovery
   returning 0 perps or >15s means the probe in step 0 of
   `/add-exchange` was wrong — go back to it.
3. **Boots just this connector** in isolation (no other exchanges, no
   FastAPI, no WS push loop) and streams for the window.
4. **Checks BTCUSDT leg** for all four fields: `mark_price > 0`,
   `funding_rate is not None`, `next_funding_time is not None`,
   `funding_interval_h is not None`. Any missing → FAIL.
5. **Interval-cache sanity**: flags if EVERY symbol resolved to the
   `default_funding_interval_h` — almost always means the discovery
   `_interval_cache` wasn't wired through `pair_discovery.py`.

## Interpreting failures

| Symptom | Likely cause |
|---|---|
| Discovery returned 0 perps | Wrong filter (`settleCcy`, `state`, `ctType`), or UA-blocked |
| `mark_price = 0` on BTCUSDT after 60s | Wrong field name in `_handle_message` or subscribe never sent |
| `funding_rate = None` | Venue ships rate on a different channel or REST-only — revisit archetype choice |
| `funding_interval_h = None` | No `_interval_cache` wired OR runtime-derivation logic (Archetype 4) broken |
| Every symbol on default fih | `_interval_cache` exists but `_set_interval_cache` isn't being called from `pair_discovery.py` |
| Import fails with "missing keys: ['fee_source_url']" | Add `fee_source_url` to the `EXCHANGES` entry before re-running |

## Deposit / withdraw status (gap #8 — not yet automated)

`backend/exchange/asset_status.py` currently polls Binance bapi only.
Other venues have their own endpoints:

- Bybit: `GET /v5/asset/coin/query-info`
- OKX: `GET /api/v5/asset/currencies` (requires auth — skip for now)
- Bitget: `GET /api/v2/spot/public/coins`

We treat Binance as the source-of-truth for deposit/withdraw across all
venues (assumption: if Binance delists, the coin is effectively
un-arbitrageable). When adding a venue, do NOT wire its own status
endpoint unless the user explicitly asks. Just confirm the pair appears
in `/api/pairs` with a populated `coin_status` object.

## When verify passes

1. Update `changelog.md` with the Phase entry (see
   `/add-exchange` step 6).
2. Commit. The user's memory says every `git push` must append an entry
   to `changelog.md` — that's this same Phase entry, no separate log.
