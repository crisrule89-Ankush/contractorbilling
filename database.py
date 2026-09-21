"""Database connection helpers for the application.

The hosted SQL Server uses a legacy TLS configuration that Windows ODBC cannot
negotiate on this machine. python-tds connects using the SQL Server TDS
protocol and encrypts the login exchange without relying on Windows Schannel.

Connections opened during a Flask request are tracked on the application
context and closed automatically when the request ends, so a route that raises
part way through cannot leak its connection.
"""

import os

import pytds
from dotenv import load_dotenv

load_dotenv()

try:
    from flask import g, has_app_context
except ImportError:  # allows the standalone maintenance scripts to import this
    g = None

    def has_app_context():
        return False


class CursorAdapter:
    """Keep the existing application's pyodbc-style ``?`` parameters working."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._closed = False

    def execute(self, operation, params=None):
        if params is None:
            return self._cursor.execute(operation)
        return self._cursor.execute(operation.replace("?", "%s"), params)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._cursor.close()
        except Exception:
            pass

    def __getattr__(self, name):
        try:
            cursor = object.__getattribute__(self, "_cursor")
        except AttributeError:
            raise AttributeError(name)
        return getattr(cursor, name)


class ConnectionAdapter:
    def __init__(self, connection):
        self._connection = connection
        self._closed = False

    @property
    def closed(self):
        return self._closed

    def cursor(self):
        return CursorAdapter(self._connection.cursor())

    def close(self):
        """Close the connection. Safe to call more than once."""
        if self._closed:
            return
        self._closed = True
        try:
            self._connection.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def __getattr__(self, name):
        try:
            connection = object.__getattribute__(self, "_connection")
        except AttributeError:
            raise AttributeError(name)
        return getattr(connection, name)


def _track(adapter):
    """Remember a connection so the request teardown can close it."""
    if g is None or not has_app_context():
        return
    tracked = getattr(g, "_db_connections", None)
    if tracked is None:
        tracked = []
        setattr(g, "_db_connections", tracked)
    tracked.append(adapter)


def close_tracked_connections(exc=None):
    """Close connections left open when the request ends.

    Returns the number that were still open, which is the leak count for that
    request. Registered as a Flask ``teardown_appcontext`` handler in app.py.
    """
    if g is None or not has_app_context():
        return 0
    tracked = getattr(g, "_db_connections", None)
    if not tracked:
        return 0
    try:
        delattr(g, "_db_connections")
    except (AttributeError, KeyError):
        pass
    leaked = 0
    for adapter in tracked:
        if not adapter.closed:
            leaked += 1
            adapter.close()
    return leaked


def get_connection():
    required_settings = ("DB_SERVER", "DB_DATABASE", "DB_USER", "DB_PASSWORD")
    missing_settings = [name for name in required_settings if not os.environ.get(name)]
    if missing_settings:
        raise RuntimeError(
            "Missing database configuration: " + ", ".join(missing_settings) + ". "
            "Set these in the environment or .env file."
        )

    connection = pytds.connect(
        server=os.environ["DB_SERVER"],
        port=int(os.environ.get("DB_PORT", "1433")),
        database=os.environ["DB_DATABASE"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        login_timeout=10,
        timeout=30,
        enc_login_only=True,
        row_strategy=pytds.namedtuple_row_strategy,
    )
    adapter = ConnectionAdapter(connection)
    _track(adapter)
    return adapter
