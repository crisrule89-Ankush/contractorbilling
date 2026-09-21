# Contractor vs Billing — Escon Management System

Flask application for contractor and billing management, backed by SQL Server.

## Requirements

- Python 3.10+
- Network access to the SQL Server instance
- (Optional) Apache/XAMPP or IIS if you want to serve it behind a reverse proxy

## Setup

Create a virtual environment and install dependencies:

```
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Do not copy a `venv` folder between machines — a virtualenv hardcodes the path
to the Python that created it and will not start elsewhere. Always recreate it
with the commands above.

## Secure configuration

Copy `.env.example` to `.env` and set every value. The app reads these values
when it starts; `.env` is ignored by Git and must never be committed.

```
Copy-Item .env.example .env
```

Set `FLASK_SECRET_KEY`, `DB_SERVER`, `DB_PORT`, `DB_DATABASE`, `DB_USER`, and
`DB_PASSWORD` in `.env`. In IIS or Apache production deployments, set the
same values as process environment variables instead.

Verify the connection:

```
venv\Scripts\python.exe test_connection.py
```

## Schema

Run the `.sql` files against the target database if the tables do not exist.
All of them are safe to re-run:

- `create_adbillingmaster.sql` — billing table
- `add_unique_billing_constraint.sql` — unique key constraint on billing
- `add_contractor_location.sql` — adds the `ContractorLocation` column

The `UserLogin`, `AdContractorMaster`, `AppSettings` and `FormFieldConfig`
tables are expected to already exist. `AppSettings` and `FormFieldConfig` are
created automatically on first use.

## Running

```
venv\Scripts\python.exe run_5002.py
```

Serves on http://127.0.0.1:5002 using waitress. Open that address directly, or
put a reverse proxy in front of it.

### Behind Apache (XAMPP)

Add a vhost that proxies to the app, then browse to the chosen port:

```
Listen 8086
<VirtualHost *:8086>
    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:5002/ retry=0 timeout=600 disablereuse=On
    ProxyPassReverse / http://127.0.0.1:5002/
</VirtualHost>
```

`disablereuse=On` matters: without it Apache reuses pooled backend sockets and
returns intermittent 502 "error reading status line" responses.

`web.config` contains the equivalent rewrite rule for IIS (port 5001).

## Roles

- **admin / head office** — all branches, branch dropdown on Billing Schedule
  and Reports, may delete billing entries
- **branch logins** — restricted to their own branch for both data entry and
  report downloads

## Notes

- Billing `BranchName` is the branch the work was done for. `ContractorLocation`
  is the contractor's own branch, mapped from the Contractor Code. They are
  intentionally independent.
- A billing entry's unique key is `ContractorCode_BillNo`. Save creates new
  records only; Update edits existing ones and cannot change the key.
