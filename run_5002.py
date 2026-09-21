"""Serve the app on 127.0.0.1:5002 behind the XAMPP/Apache reverse proxy.

Uses waitress rather than Flask's development server: the dev server closes
idle keep-alive connections, which makes Apache's pooled backend sockets go
stale and return 502 "error reading status line" (AH01102).
"""

import os

from app import app

# Local use stays on 127.0.0.1:5002. Render supplies PORT and requires the
# service to listen on every interface, so use 0.0.0.0 whenever PORT is set.
PORT = int(os.environ.get("PORT", "5002"))
HOST = os.environ.get("HOST") or ("0.0.0.0" if "PORT" in os.environ else "127.0.0.1")

if __name__ == "__main__":
    try:
        from waitress import serve
    except ImportError:
        print("waitress not installed - falling back to the Flask dev server.")
        print("Install it with:  pip install waitress")
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    else:
        print(f"Serving on http://{HOST}:{PORT} (waitress)")
        serve(app, host=HOST, port=PORT, threads=8, channel_timeout=600)
