# XAMPP Server Deployment

This package is isolated from existing XAMPP applications:

- It installs into `C:\xampp\apps\ContractorVSBilling`, not `htdocs`.
- It listens only on `127.0.0.1:5002`, so it does not expose or replace an
  existing website.
- It does not edit or restart Apache, MySQL, PHP, or another application.

Run PowerShell **as the Windows user that will run the app**. Change the ZIP
path below to the file you downloaded.

```powershell
$Package = "C:\Users\Administrator\Downloads\ContractorVSBilling-deployment.zip"
$AppRoot = "C:\xampp\apps\ContractorVSBilling"

if (Test-Path -LiteralPath $AppRoot) {
    throw "Deployment stopped: $AppRoot already exists. No files were changed."
}

New-Item -ItemType Directory -Path $AppRoot -Force | Out-Null
Expand-Archive -LiteralPath $Package -DestinationPath $AppRoot
Set-Location $AppRoot
```

Create the private configuration file, then open it and enter the production
SQL Server values. Do not put passwords into this guide or commit `.env`.

```powershell
Copy-Item .env.example .env
notepad .env
```

The `.env` file must contain a long random `FLASK_SECRET_KEY` and the correct
`DB_SERVER`, `DB_PORT`, `DB_DATABASE`, `DB_USER`, and `DB_PASSWORD` values.

Install Python dependencies and test the SQL connection:

```powershell
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe test_connection.py
```

Start the app in its own background process and write logs only inside its own
application folder. The command stops safely if another application already
uses port 5002; it does not stop or reconfigure that application.

```powershell
$LogRoot = Join-Path $AppRoot "logs"
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

if (Get-NetTCPConnection -LocalPort 5002 -State Listen -ErrorAction SilentlyContinue) {
    throw "Deployment stopped: port 5002 is already in use. No existing application was changed."
}

Start-Process -FilePath "$AppRoot\venv\Scripts\python.exe" `
  -ArgumentList "run_5002.py" `
  -WorkingDirectory $AppRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput "$LogRoot\waitress.out.log" `
  -RedirectStandardError "$LogRoot\waitress.err.log"

Start-Sleep -Seconds 3
Invoke-WebRequest http://127.0.0.1:5002/ -UseBasicParsing | Select-Object StatusCode
```

Open `http://127.0.0.1:5002/` on the server. This is the only required setup
and does not affect another XAMPP application.

## Optional Apache access

Only if users need to access this application remotely, ask the XAMPP
administrator to add a dedicated proxy site on an unused port such as 8086.
First validate that port 8086 is unused and Apache configuration is valid.
This optional step may briefly restart Apache, so schedule it separately from
the isolated application deployment above.
