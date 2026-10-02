"""Localhost receiver: the user's own browser POSTs files it already fetched (EMMA PDFs) here, so nothing is
re-requested from EMMA. Usage: python3 scripts/local_receiver.py <out_dir> [port]. POST /save?name=x.pdf"""
import http.server, os, sys, urllib.parse
OUT = sys.argv[1]; PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8799
class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_POST(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        name = os.path.basename(q.get("name", ["file.bin"])[0])
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        open(os.path.join(OUT, name), "wb").write(data)
        self.send_response(200); self._cors(); self.end_headers(); self.wfile.write(f"saved {name} {len(data)}".encode())
    def log_message(self, fmt, *a): sys.stderr.write((fmt % a) + "\n")
http.server.HTTPServer(("127.0.0.1", PORT), H).serve_forever()
