#!/usr/bin/env python3
"""Serve the built site locally with its Cloudflare-style deep-box fallback.

Run after building: python3 site/preview_server.py
This binds to loopback only and does not publish the site.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

DIST = Path(__file__).resolve().parent / "dist"
PORT = 4321


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def send_head(self):
        path = urlsplit(self.path).path.rstrip("/")
        target = DIST / path.lstrip("/")
        if (
            not target.is_file()
            and not (target / "index.html").is_file()
            and any(path.startswith(f"/{gov}/box/") for gov in ("city", "cps", "parks"))
        ):
            original = self.path
            self.path = "/box-shell/"
            try:
                return super().send_head()
            finally:
                self.path = original
        return super().send_head()


if __name__ == "__main__":
    if not (DIST / "index.html").is_file():
        raise SystemExit("Build the site first: npm --prefix site run build")
    print(f"Local preview: http://127.0.0.1:{PORT}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), PreviewHandler).serve_forever()
