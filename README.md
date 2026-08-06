# Farm Finance Tracker

A Flask and SQLite application for tracking fields, seasons, farming operations, income, expenses, and profit/loss. The project turns common farm bookkeeping workflows into a simple web dashboard.

## Features

- Account registration and session-based login
- Multiple fields with parcel and area information
- Seasonal income and expense entries by category
- Harvest, grant, fuel, fertilizer, seed, labour, insurance, rent, and other records
- Per-field and overall profit/loss summaries
- Ownership checks that prevent users from modifying another user's fields

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Set a private session secret before running:

```powershell
$env:FLASK_SECRET_KEY='replace-with-a-random-local-secret'
python app.py
```

Open `http://127.0.0.1:5500`. The database and complete schema are created automatically on first run.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover clean database initialization, password hashing, login, password validation, and cross-user field protection.

## Screenshots

The privacy-safe screenshot checklist and expected filenames are documented in `docs/screenshots/README.md`.

## Security

- Passwords are stored using Werkzeug password hashes.
- Existing legacy plaintext test passwords are upgraded after a successful login.
- The Flask session key comes from `FLASK_SECRET_KEY`.
- Runtime databases are ignored and must not be published.

## Portfolio status

The current version preserves the original coursework interface while hardening authentication and installation. A future version can consolidate the repeated category routes into reusable blueprints and services.

## License

MIT
