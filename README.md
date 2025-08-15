# Tron Bot Boilerplate

A production-ready Python boilerplate for building Telegram or service bots that accept TRON (TRX) payments. It provides a clean architecture, TRON wallet management, deposit monitoring, and withdrawal processing so you can focus on your bot logic.

This repository is intentionally generic: no logic or business rules are included.

## Version

Current version: 1.0.0

## Highlights

- __TRON payments__: deposit monitoring and withdrawal processing
- __Per-user wallets__: secure generation and encrypted private keys
- __Clean architecture__: clear separation of bot, services, blockchain, database, workers, and utilities
- __PostgreSQL + SQLAlchemy__: robust persistence layer
- __Background jobs with APScheduler__: periodic workers for payments and housekeeping
- __Straightforward setup__: direct Python execution

## Project Structure

```
tron-bot-boilerplate/
├── main.py                 # Application entrypoint
├── config.py               # Centralized configuration
├── blockchain/
│   └── tron_client.py      # TRON RPC client integration
├── bot/
│   ├── handlers/           # Bot command/message handlers
│   ├── keyboards.py        # Keyboard layouts
│   ├── messages.py         # Message building & formatting
│   ├── utils.py            # Bot helpers/utilities
│   └── ...                 # Other bot modules
├── services/
│   ├── user_service.py     # User management
│   ├── wallet_service.py   # Wallet generation & management
│   ├── deposit_service.py  # Deposit monitoring & processing
│   ├── withdrawal_service.py # Withdrawals & limits
│   └── ...                 # Other domain services
├── database/
│   ├── models.py           # SQLAlchemy ORM models
│   ├── database.py         # DB session/engine
│   └── migrations/         # Alembic migrations
├── workers/
│   ├── deposit_monitor.py  # Periodic deposit check
│   └── withdrawal_processor.py # Periodic withdrawal processing
├── utils/
│   ├── encryption.py       # Symmetric encryption helpers
│   ├── validators.py       # Input validation
│   ├── helpers.py          # Misc helpers
│   └── logger.py           # Logging setup
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
└── generate_key.py         # Helper to generate encryption key
```

Note: File names listed above reflect the typical layout in this repo; keep your own modules as needed.

## Requirements

- Python 3.10+
- PostgreSQL 13+

## Installation

1) Clone the repository
```bash
git clone https://github.com/Ismael237/tron-bot-boilerplate.git
cd tron-bot-boilerplate
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
copy .env.example .env
```
Then edit `.env` and set your values

5) Initialize the database
```bash
alembic upgrade head
```

## Run

Start the app directly with Python:
```bash
python main.py
```

Logs are typically written under `logs/` as configured by your `.env`.

## TRON Payment Flow (Overview)

- __Wallets__: a secure master private key is used to derive or fund per-user wallets. Private keys are encrypted at rest.
- __Deposits__: workers watch incoming transactions to user wallets and credit balances when confirmed.
- __Withdrawals__: requests are validated and processed periodically with optional fees and daily limits.

You can adapt handlers and services to match your bot UX (Telegram commands, menus, or service endpoints).

## Security Best Practices

- __Protect secrets__: never commit `.env` or private keys; use a different key per environment.
- __Encrypt at rest__: ensure `ENCRYPTION_KEY` is 32 bytes and rotate when needed; re-encrypt stored secrets on rotation.
- __Limit withdrawals__: configure `MIN_WITHDRAWAL_AMOUNT` and daily limits; validate destination addresses.
- __Validate inputs__: sanitize and validate all user-provided data.
- __Least privilege__: lock down DB and node/API credentials; prefer read-only keys where possible.
- __Monitor & alert__: capture errors and anomalies; review logs regularly.

## Troubleshooting

- Database errors: verify `DATABASE_URL` and that migrations ran: `alembic upgrade head`.
- TRON RPC issues: check `TRON_API_URL` reachability and API key requirements (if any).
- Missing env vars: ensure `.env` matches `.env.example` and values are set.
- Permissions: make sure the process can write to `logs/`.

## License

Apache License 2.0

This project is made available under the Apache License, Version 2.0. You may use it in your own bot, including commercially, provided that you retain attribution. Please keep the following notice in your distributions and documentation:

NOTICE: This product includes software developed by the Tron Bot Boilerplate project and its contributors.

See https://www.apache.org/licenses/LICENSE-2.0 for the full license text.

## Credits

If you use this boilerplate, please credit “Tron Bot Boilerplate” in your project README, docs, or About page.