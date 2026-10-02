#!/usr/bin/env python3
"""Light, human-paced fetch of single EMMA (emma.msrb.org) pages and files, for the bond-series task.

The user approved light use for this one task: at most one page or file load every 4 seconds, hard cap
300 loads, every URL logged to raw/emma_manual/requests.log. No crawling, no trade data.

Usage:
  python3 scripts/emma_fetch.py page <url> <out.html>        # throwaway headless Chrome (CDP), saves rendered HTML
  python3 scripts/emma_fetch.py text <url> <out.txt>         # same, saves visible text (document.body.innerText)
  python3 scripts/emma_fetch.py file <url> <out.pdf>         # plain curl for a direct document link
  python3 scripts/emma_fetch.py count                        # loads used so far

Several pages can be loaded in one Chrome session with `pages <outdir> <url> [<url> ...]`; each URL is one load,
the 4 second gap applies between them, and the output file name is derived from the URL's last segment.

Chrome uses a temp --user-data-dir that is deleted afterwards. Nothing from the user's profiles is touched.
Needs: pip websocket-client.

STATUS 2026-10-02: EMMA answered HTTP 403 (server awselb/2.0, no page) to default headless Chrome and to default curl.
It answered 200 only when the client presented a normal browser user agent. This script does NOT spoof one, because the
MSRB Terms of Use forbid bypassing measures meant to limit automated access and the approval covered paced headless
Chrome / curl, not evading a block. So as shipped it gets 403 from EMMA. Ask the user before changing that.
"""
import json, os, re, subprocess, sys, tempfile, time, shutil, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTDIR = os.path.join(ROOT, "raw", "emma_manual")
LOG = os.path.join(OUTDIR, "requests.log")
STATE_TS = os.path.join(OUTDIR, ".last_load_ts")
CAP = 300
GAP = 4.0
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
os.makedirs(OUTDIR, exist_ok=True)


def used():
    if not os.path.exists(LOG):
        return 0
    return sum(1 for ln in open(LOG) if ln.strip() and not ln.startswith("#"))


def gate(url, kind):
    """Enforce the cap and the 4 second gap, then log the load BEFORE it happens."""
    if used() >= CAP:
        sys.exit(f"hard cap of {CAP} loads reached, refusing")
    if "emma.msrb.org" not in url and "msrb.org" not in url:
        sys.exit("only emma.msrb.org / msrb.org URLs are allowed in this script")
    last = float(open(STATE_TS).read()) if os.path.exists(STATE_TS) else 0.0
    wait = GAP - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    now = time.time()
    open(STATE_TS, "w").write(str(now))
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\t{kind}\t{url}\n")


def safe_name(url):
    s = re.sub(r"[^A-Za-z0-9]+", "_", url.split("emma.msrb.org/")[-1]).strip("_")
    return s[:120]


class Browser:
    def __init__(self, port=9444):
        import websocket
        self.websocket = websocket
        self.port = port
        self.prof = tempfile.mkdtemp(prefix="emmacap_")
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={self.prof}",
             "--no-first-run", f"--remote-allow-origins=http://127.0.0.1:{port}", "--window-size=1400,2000",
             "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tabs = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
            except Exception:
                time.sleep(0.25)
        self.ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=60)
        self.n = 0
        self.call("Page.enable")

    def call(self, method, params=None):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == mid:
                return m.get("result", {})

    def eval(self, js):
        r = self.call("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value")

    def load(self, url, settle=6.0, ready_js=None, max_wait=45):
        self.call("Page.navigate", {"url": url})
        t0 = time.time()
        time.sleep(settle)
        while ready_js and time.time() - t0 < max_wait:
            if self.eval(ready_js):
                break
            time.sleep(1.5)

    def close(self):
        try:
            self.proc.terminate(); self.proc.wait(10)
        except Exception:
            pass
        shutil.rmtree(self.prof, ignore_errors=True)


def run_pages(urls, outs, mode="html", ready_js=None, settle=6.0):
    b = Browser()
    try:
        for url, out in zip(urls, outs):
            gate(url, "page")
            b.load(url, settle=settle, ready_js=ready_js)
            js = "document.documentElement.outerHTML" if mode == "html" else "document.body.innerText"
            data = b.eval(js) or ""
            open(out, "w").write(data)
            print("saved", out, len(data), "loads used:", used())
    finally:
        b.close()


def fetch_file(url, out):
    gate(url, "file")
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "120", 
                        "-o", out, "-w", "%{http_code} %{size_download}", url], capture_output=True, text=True)
    print("saved", out, r.stdout, r.stderr.strip(), "loads used:", used())


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "count":
        print(used())
    elif a[0] in ("page", "text"):
        run_pages([a[1]], [a[2]], "html" if a[0] == "page" else "text")
    elif a[0] == "file":
        fetch_file(a[1], a[2])
    elif a[0] == "pages":
        outdir = a[1]; os.makedirs(outdir, exist_ok=True)
        urls = a[2:]
        run_pages(urls, [os.path.join(outdir, safe_name(u) + ".html") for u in urls])
    else:
        sys.exit(__doc__)
