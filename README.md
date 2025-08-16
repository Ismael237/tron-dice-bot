# TronDiceBot

A Telegram dice game bot built on the TRON (TRX) blockchain. Users bet on a 1–100 dice roll with a fixed house edge, provably fair randomness, secure TRX payments, and transparent tracking.

## Version

Current version: 1.0.0 (MVP)

## Highlights

- **Provably fair dice game** with server/client seeds and nonces
- **TRON payments**: deposit monitoring, per-user wallets, withdrawals
- **Game features**: challenges, leaderboards, referrals, history and stats
- **Admin & monitoring**: admin dashboards, alerts, scheduled jobs
- **Clean architecture** with PostgreSQL + SQLAlchemy and APScheduler
- **Production-ready** logging, configuration via `.env`

## Project Structure

```
tron-dice-bot/
├── main.py                      # App entry point; starts bot + scheduler
├── config.py                    # Centralized configuration
├── blockchain/
│   └── tron_client.py           # TRON RPC client integration
├── bot/
│   ├── handlers/                # Telegram handlers (game, wallet, admin, etc.)
│   ├── keyboards.py             # Keyboard layouts
│   ├── messages.py              # Message templates & formatting
│   └── utils.py                 # Bot helpers
├── services/
│   ├── game_service.py          # Core game mechanics
│   ├── fairness_service.py      # Provably fair seeds + verification
│   ├── deposit_service.py       # Deposits monitoring/crediting
│   ├── withdrawal_service.py    # Withdrawals & limits
│   ├── wallet_service.py        # Wallet generation & security
│   ├── user_service.py          # User management & stats
│   ├── referral_service.py      # Referral tracking & commissions
│   ├── challenge_service.py     # Daily challenges
│   ├── leaderboard_service.py   # Rankings & aggregation
│   └── admin_service.py         # Admin metrics and controls
├── database/
│   ├── models.py                # SQLAlchemy ORM models
│   ├── database.py              # Session/engine init
│   └── migrations/              # Alembic migrations
├── workers/
│   ├── deposit_monitor.py       # Periodic deposit confirmations
│   ├── withdrawal_processor.py  # Periodic withdrawal processing
│   ├── challenge_worker.py      # Challenge updates & resets
│   ├── leaderboard_worker.py    # Leaderboards aggregation
│   └── admin_monitor.py         # Admin alerts & monitoring
├── utils/
│   ├── encryption.py            # Symmetric encryption helpers
│   ├── validators.py            # Input validation
│   ├── helpers.py               # Misc helpers
│   └── logger.py                # Logging setup
├── tests/                       # Unit & integration tests
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
└── generate_key.py              # Helper to generate encryption key
```

## Requirements

- Python 3.10+
- PostgreSQL 13+

## Installation

1) Clone the repository
```bash
git clone https://github.com/Ismael237/tron-dice-bot.git
cd tron-dice-bot
```

2) Create and activate a virtual environment

Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```

Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

3) Install dependencies
```bash
pip install -r requirements.txt
```

4) Create your environment file
```bash
copy .env.example .env   # Windows
# or
cp .env.example .env     # Linux/macOS
```
Then edit `.env` and set your values.

5) Initialize the database
```bash
alembic upgrade head
```

## Key Environment Variables (.env)

- Telegram
  - `TELEGRAM_BOT_TOKEN` (required)
  - `TELEGRAM_ADMIN_ID`, `TELEGRAM_ADMIN_USERNAME`, `BOT_USERNAME`
- Database
  - `DATABASE_URL` (e.g. postgresql://user:pass@localhost:5432/bot)
- TRON / Payments
  - `TRON_PRIVATE_KEY` (master key for funding/ops)
  - `TRON_API_URL` (e.g. https://api.trongrid.io)
  - `TRON_EXPLORER_URL`
  - `DEPOSIT_CONFIRMATIONS_REQUIRED`
  - `DEPOSIT_TO_MAIN_WALLET_RATE`, `WITHDRAWAL_FEE_RATE`
- Game & Limits
  - `HOUSE_EDGE`, `MIN_BET_AMOUNT`, `MAX_BET_AMOUNT`
  - `DAILY_WITHDRAWAL_LIMIT`, `MIN_WITHDRAWAL_AMOUNT`, `ITEMS_PER_PAGE`
  - `REFERRAL_RATE`
- Scheduler & Monitoring
  - `DEPOSIT_CHECK_INTERVAL`, `WITHDRAWAL_PROCESS_INTERVAL`
  - `AP_SCHEDULER_THREAD_POOL_SIZE`
  - `ADMIN_BIG_WIN_TRX`, `ADMIN_HOT_WALLET_MIN_TRX`, `ADMIN_SPIKE_GAMES_PER_MIN`
  - `EMERGENCY_STOP`
- Security & Logging
  - `ENCRYPTION_KEY` (32 bytes), `LOG_LEVEL`, `LOG_FILE`, `ERROR_LOG_FILE`

See `.env.example` for defaults and full list.

## Run

Start the bot directly with Python:
```bash
python main.py
```
Logs are written as configured in `.env`.

### Scheduled Jobs
APScheduler is configured in `main.py` (`start_scheduler()`):
- Deposits: `workers/deposit_monitor.py`
- Withdrawals: `workers/withdrawal_processor.py`
- Challenges: periodic updates + daily reset
- Leaderboards: aggregation and notifications
- Admin monitor: alerts and daily/periodic summaries

## Telegram Commands (examples)

- `/start`, `/help`, `/settings`, `/about`, `/support`, `/qa`
- `/play`, `/stats`, `/history`
- `/deposit`, `/withdraw`, `/balance`
- `/leaderboard`, `/challenges`, `/referral`
- Admin: `/admin`, `/admin_stats`, `/admin_users`, `/admin_games`, `/admin_alerts`

## Provably Fair

Implemented in `services/fairness_service.py` using server/client seeds and nonces.
- Server seed hash is committed before play; seed is revealed after.
- Users can verify results using the same HMAC-SHA256 process described in `devbook.md`.

## Testing

```bash
pytest -q
```
See `tests/` for unit and integration tests (fairness, game engine, integration).

## Security Best Practices

- **Protect secrets**: never commit `.env` or private keys.
- **Encrypt at rest**: `ENCRYPTION_KEY` must be 32 bytes; rotate and re-encrypt secrets as needed.
- **Withdrawal limits**: configure min/daily limits; validate TRON addresses.
- **Input validation**: sanitize all user inputs.
- **Least privilege**: restrict DB and API credentials.
- **Monitor & alert**: review logs and admin alerts regularly.

## Troubleshooting

- Database errors: verify `DATABASE_URL` and run `alembic upgrade head`.
- TRON RPC issues: check `TRON_API_URL` reachability and keys/quotas.
- Missing env vars: ensure `.env` matches `.env.example` and values are set.
- Permissions: ensure process can write to the configured log files.

## License

Apache License 2.0

This project is made available under the Apache License, Version 2.0. See https://www.apache.org/licenses/LICENSE-2.0 for the full license text.

## Credits

If you use this project, please credit “TronDiceBot” in your README/docs.