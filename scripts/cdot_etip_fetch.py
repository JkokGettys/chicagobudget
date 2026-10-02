"""Fetch CMAP eTIP (public site cmap.ecointeractive.com) project lists and project detail JSON for one plan cycle.
Uses the same public headers the website's own front end sends to every visitor (tenantConfig.json).
usage: scripts/cdot_etip_fetch.py (writes raw/cdot/tip<cycle>/*.json). usage: cdot_etip_fetch.py <planCycleId> <orgId> <label>"""
import json, sys, os, time, urllib.request
A = "https://api-pwi-prod.ecointeractive.com"
H = {"x-system-key": "25f54926-8e32-4d87-80d2-bbe76e97db7c",
     "x-organization-key": "7fe54a07-a62d-4695-a985-cb75d1640961", "content-type": "application/json"}
def call(path, body=None):
    req = urllib.request.Request(A + path, data=json.dumps(body).encode() if body is not None else None, headers=H,
                                 method="POST" if body is not None else "GET")
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as e:
            time.sleep(2 + i * 3); err = e
    raise err
if __name__ == "__main__":
    cyc, org, label = sys.argv[1:4]
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw", "cdot"); out = f"{d}/tip{cyc}"; os.makedirs(out, exist_ok=True)
    g = call(f"/api/v1/public/ProjectRevisions/grid?PlanCycleId={cyc}", {"PlanCycleId": cyc, "OrganizationIds": [org]})
    json.dump(g, open(f"{d}/grid_{cyc}_{label}.json", "w"))
    rows = [r for r in g["view"]["rows"] if r.get("actionLink")]
    print(label, len(rows), "projects")
    for r in rows:
        al = r["actionLink"]; rid = al["resourceId"]; fn = f"{out}/{rid}.json"
        if os.path.exists(fn): continue
        json.dump(call(f"/api/v1/public/ProjectRevisions/{rid}"), open(fn, "w"))
