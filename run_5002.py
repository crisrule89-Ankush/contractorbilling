"""Serve the app on 127.0.0.1:5002 behind the XAMPP/Apache reverse proxy.

Uses waitress rather than Flask's development server: the dev server closes
idle keep-alive connections, which makes Apache's pooled backend sockets go
stale and return 502 "error reading status line" (AH01102).
"""

from app import app

HOST = "127.0.0.1"
PORT = 5002

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
