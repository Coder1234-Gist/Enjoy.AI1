# Recommendation Bot

A Telegram bot that recommends Movies, Web Series, Novels, Light Novels, and
Manga, filtered by genre and year, with clickable detail views and an
optional daily digest.

## What's inside

```
telegram_bot/
├── main.py                    # entry point
├── config.py                  # env var loading
├── genres.py                  # genre taxonomies per category
├── database.py                # SQLite: users, subscriptions, last filters
├── keyboards.py                # all inline keyboard builders
├── scheduler.py                # daily digest job
├── handlers/
│   ├── conversation.py         # the wizard: category → genre → year → count → results → detail
│   └── subscription.py         # /help /subscribe /unsubscribe
├── services/
│   ├── tmdb_service.py         # Movies + Web Series (themoviedb.org)
│   ├── jikan_service.py        # Light Novels + Manga (MyAnimeList via Jikan)
│   ├── books_service.py        # Novels (Google Books)
│   └── news_service.py         # optional "industry news" for the digest
├── requirements.txt
└── .env.example
```

## Data sources (why these, and their limits)

| Category      | Source        | API key needed? | Notes |
|---------------|---------------|------------------|-------|
| Movies        | TMDb          | Yes (free)       | Rich genre filtering, ratings, cast |
| Web Series    | TMDb          | Yes (free)       | Same API, `/tv` endpoints |
| Novels        | Google Books  | No (optional)    | No genre IDs — searches by subject keyword; ratings are sparse |
| Light Novels  | Jikan (MAL)   | No               | Unofficial API, rate-limited (~3 req/sec) |
| Manga         | Jikan (MAL)   | No               | Same as above |

Industry news in the daily digest is powered by NewsAPI.org and is **optional** —
if you don't set `NEWSAPI_KEY`, that section is just skipped.

## Setup

1. **Create the bot**: message [@BotFather](https://t.me/BotFather) on Telegram,
   run `/newbot`, and copy the token it gives you.

2. **Get a TMDb key**: sign up free at https://www.themoviedb.org/settings/api.

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**:
   ```bash
   cp .env.example .env
   # then edit .env and fill in BOT_TOKEN and TMDB_API_KEY at minimum
   ```

5. **Run it**:
   ```bash
   python main.py
   ```

The bot uses long-polling (`run_polling`), so no public URL or webhook setup
is needed — it works from a laptop, a VPS, or any always-on machine.

## Deployment

The bot can run two ways, controlled entirely by the `USE_WEBHOOK` env var —
no code changes needed to switch:

- **Polling mode** (`USE_WEBHOOK=false`, the default): the bot repeatedly
  asks Telegram "any new messages?" No public URL needed — this is what you
  want for local testing and for a Background Worker deployment.
- **Webhook mode** (`USE_WEBHOOK=true`): Telegram pushes updates directly to
  a public URL you control. This is what lets the bot run as a Render **Web
  Service**, including on Render's free tier, since Render requires
  something bound to an HTTP port.

### Option A — Render Web Service with webhooks (free-tier friendly)

The included `render.yaml` at the project root is pre-configured for this.

1. Push the project to a GitHub repo.
2. On Render: **New +** → **Blueprint** → connect your repo. Render reads
   `render.yaml` and creates a Web Service with `USE_WEBHOOK=true` already
   set and a random `WEBHOOK_SECRET` auto-generated.
3. You'll be prompted for the secret env vars (`BOT_TOKEN`, `TMDB_API_KEY`,
   etc.) — enter them there.
4. Deploy. Render automatically provides `RENDER_EXTERNAL_URL` and `PORT`
   at runtime, so no extra config is needed — check the logs for `Bot
   starting in webhook mode at https://...`.

**Trade-off to know about:** on the Free plan, the filesystem resets on
every spin-down/redeploy, so subscriptions and saved filters won't persist
between restarts. If that matters to you, switch `plan: free` to
`plan: starter` in `render.yaml` and uncomment the `disk:` block — that
adds a small persistent volume for the SQLite file (details are commented
in the file itself).

Prefer to set it up by hand instead of via Blueprint? Create a **Web
Service** (not Background Worker), set:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Environment**: `USE_WEBHOOK=true`, plus `BOT_TOKEN`, `TMDB_API_KEY`, etc.

Render sets `PORT` and `RENDER_EXTERNAL_URL` for you automatically either way.

### Option B — Render Background Worker (polling, paid only)

If you'd rather keep things simple and don't mind the $7/month Starter
plan (Background Workers have no free tier), use
`deploy/render-worker.yaml` instead — it deploys the bot in plain polling
mode, no webhook setup required. Same Blueprint flow as above, just point
Render at that file instead of the root `render.yaml`.

### Option C — Docker (any server you control)

Works identically on a VPS, a Raspberry Pi, or your own machine. Uses
polling mode by default (no webhook setup needed).

```bash
cp .env.example .env   # fill in BOT_TOKEN, TMDB_API_KEY, etc.
docker compose up -d --build
docker compose logs -f   # check it started cleanly
```

`docker-compose.yml` mounts a `./data` folder for the SQLite file and sets
`restart: unless-stopped`, so it survives reboots and crashes automatically.
To update after pulling new code: `docker compose up -d --build` again.

### Option D — A Linux VPS with systemd (no Docker)

Good if you want it running as a native background service, in polling mode.

```bash
# on the server
sudo mkdir -p /opt/telegram_bot
sudo cp -r telegram_bot/* /opt/telegram_bot/
cd /opt/telegram_bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env   # fill in your keys

sudo useradd -r -s /bin/false botuser   # dedicated non-login user (optional but safer)
sudo chown -R botuser:botuser /opt/telegram_bot

sudo cp deploy/recommendation-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now recommendation-bot
sudo systemctl status recommendation-bot   # confirm it's running
journalctl -u recommendation-bot -f        # tail logs
```

This restarts the bot automatically on crash or server reboot.

### A few things that matter regardless of where you run it

- Only ever run **one instance** of the bot at a time against the same
  token. In polling mode, a second instance causes `Conflict: terminated
  by other getUpdates request` errors. In webhook mode, deploying a second
  instance just silently overwrites the first one's webhook registration.
- Keep `.env` out of version control (already covered by `.dockerignore`;
  add a `.gitignore` with `.env` and `bot_data.db` if you push this to git).
- Back up `bot_data.db` (or your persistent volume) periodically if you're
  relying on it — it's the only thing that isn't reproducible from the code.

## Using the bot

- `/start` — walks through Category → Genre → Year (specific or all-time) →
  Top 5/10 → results. Tap any result for a detail card (poster, summary,
  cast/authors, rating). "Change filters" and "Start over" are always
  available; every step also has a "Back" button.
- `/subscribe` / `/unsubscribe` — toggle the daily digest (also available as
  a button under `/help`).
- `/cancel` — reset mid-flow.

## Extending it

- **Add a genre**: edit the relevant dict in `genres.py`.
- **Add a data source** (e.g. a different books API, or a light-novel
  aggregator with English titles): drop a new module in `services/`
  following the pattern in `books_service.py` (a `discover()` and a
  `get_details()` function returning the same normalized dict shape used
  elsewhere), then add a branch in `_fetch_recommendations` /
  `_fetch_details` in `handlers/conversation.py`.
- **Personalization**: `database.py` already stores each user's last-used
  category/genre (`get_last_filters`) — you could use that to pre-select
  filters or power a "Recommend based on my usual taste" shortcut.
- **Scaling the daily digest**: for a large user base, batch sends with a
  short `asyncio.sleep` between messages to stay under Telegram's rate
  limits (~30 messages/second across all chats).

## Notes on rate limits

- Jikan (MAL) is the strictest — a few requests per second. The bot already
  keeps calls minimal (one `discover` call for a search, one `get_details`
  call per item viewed), but if you expect heavy traffic, consider adding a
  short cache.
- TMDb and Google Books are generous for a project like this.
