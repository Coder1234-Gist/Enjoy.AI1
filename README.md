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

The bot uses long-polling, so any machine that stays online and can reach
`api.telegram.org` works — no domain or open inbound port needed. Pick
whichever of these fits how you want to manage it:

### Option A — Docker (recommended if you're comfortable with it)

Works identically on a VPS, a Raspberry Pi, or your own machine.

```bash
cp .env.example .env   # fill in BOT_TOKEN, TMDB_API_KEY, etc.
docker compose up -d --build
docker compose logs -f   # check it started cleanly
```

`docker-compose.yml` mounts a `./data` folder for the SQLite file and sets
`restart: unless-stopped`, so it survives reboots and crashes automatically.
To update after pulling new code: `docker compose up -d --build` again.

### Option B — A Linux VPS with systemd (no Docker)

Good if you want it running as a native background service.

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

### Option C — A PaaS (Railway, Render, Fly.io, etc.) — easiest, no server to manage

These platforms build straight from the repo and keep the process alive for
you. A `Procfile` (`worker: python main.py`) is included for platforms that
use one.

1. Push this project to a GitHub repo.
2. Connect the repo on Railway/Render, and choose **Worker/Background
   Service** (not "Web Service" — this bot doesn't listen on a port).
3. Add `BOT_TOKEN`, `TMDB_API_KEY`, etc. as environment variables in the
   platform's dashboard (don't commit `.env`).
4. Deploy. Check the logs to confirm "Bot starting..." appears with no
   errors.

Note: on most of these platforms the filesystem is ephemeral (SQLite data
resets on redeploy). If subscriptions/preferences need to survive redeploys,
either attach a persistent volume (Railway and Fly.io both support this) or
swap `database.py` for a hosted Postgres instance.

### A few things that matter regardless of where you run it

- Only ever run **one instance** of the bot at a time against the same
  token — Telegram's long-polling rejects a second concurrent connection,
  and you'll see `Conflict: terminated by other getUpdates request` errors.
- Keep `.env` out of version control (already covered by `.dockerignore`;
  add a `.gitignore` with `.env` and `bot_data.db` if you push this to git).
- Back up `bot_data.db` (or your Postgres volume) periodically — it's the
  only thing that isn't reproducible from the code.

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
