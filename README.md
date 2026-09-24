# Farm Finance Tracker

A Flask and SQLite learning project for tracking fields, seasons, farming operations, income, expenses and profit/loss in a simple dashboard.

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

![Field summary](docs/screenshots/01-field-summary.png)

![Field details](docs/screenshots/02-field-details.png)

![New entry](docs/screenshots/03-new-entry.png)

## Security

- Passwords are stored using Werkzeug password hashes.
- Existing legacy plaintext test passwords are upgraded after a successful login.
- The Flask session key comes from `FLASK_SECRET_KEY`.
- Runtime databases are ignored and must not be published.

## Project status

The interface comes from the original coursework project. Authentication and installation were improved later; the category routes still have repeated logic.

## License

MIT
