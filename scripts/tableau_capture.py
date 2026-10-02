"""Capture Tableau Public bootstrap data with a throwaway headless Chrome (temp profile, nothing from the user's
profiles). Usage: python3 scripts/tableau_capture.py <view url> <out prefix>. Writes <out>_bootstrap.txt and any
later vizql responses as <out>_cmd_N.txt."""
import json, os, subprocess, sys, tempfile, time, urllib.request, websocket

url, out = sys.argv[1], sys.argv[2]
prof = tempfile.mkdtemp(prefix="tabcap_")
port = 9333
chrome = subprocess.Popen(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new",
                           f"--remote-debugging-port={port}", f"--user-data-dir={prof}", "--no-first-run", f"--remote-allow-origins=http://127.0.0.1:{port}",
                           "--window-size=1600,2000", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")); break
        except Exception:
            time.sleep(0.2)
    ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=60)
    n = [0]
    def send(method, params=None):
        n[0] += 1; ws.send(json.dumps({"id": n[0], "method": method, "params": params or {}})); return n[0]
    send("Network.enable", {"maxResourceBufferSize": 200_000_000, "maxTotalBufferSize": 400_000_000})
    send("Page.enable"); send("Page.navigate", {"url": url})
    want, pending, saved, t0 = {}, {}, 0, time.time()
    while time.time() - t0 < 90:
        try:
            m = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            break
        if m.get("method") == "Network.responseReceived":
            u = m["params"]["response"]["url"]
            if "/vizql/" in u and ("bootstrapSession" in u or "/commands/" in u):
                want[m["params"]["requestId"]] = u
        elif m.get("method") == "Network.loadingFinished" and m["params"]["requestId"] in want:
            rid = m["params"]["requestId"]; pending[send("Network.getResponseBody", {"requestId": rid})] = want.pop(rid)
        elif m.get("id") in pending:
            u = pending.pop(m["id"]); body = m.get("result", {}).get("body", "")
            name = f"{out}_bootstrap.txt" if "bootstrapSession" in u else f"{out}_cmd_{saved}.txt"
            open(name, "w").write(body); saved += 1
            print("saved", name, len(body), u[:120]); t0 = time.time() - 75  # wait ~15s more for follow-ups
finally:
    chrome.terminate()
