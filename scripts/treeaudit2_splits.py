"""Audit 2, part 2b: what did each split file (data/splits/*/*.json) actually put in the tree? Read-only.
For each split: find its target box in the snapshot (ordinance line by fund, dept, authority, account in the box's extra, or by id),
say whether the target now has children (applied), and add up the dollars of the target lines, by file.
A target found with no children, or not found, is reported as not visibly applied (the builder logs skips, we do not rerun it)."""
import glob, json, os, collections
from treeaudit2_common import *

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}; kids = children_map(rows)
    line = {}
    for r in rows:
        try: e = json.loads(r["extra"]) if r["extra"] else {}
        except Exception: e = {}
        if e.get("fund") and e.get("authority") and e.get("account") and e.get("dept_number") is not None and not r["id"].startswith("city-twice"):
            line[(str(e["fund"]), str(e["dept_number"]).lstrip("0"), str(e["authority"]), str(e["account"]))] = r
    res = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "splits", "*", "*.json"))):
        d = json.load(open(f)); gov = f.split("/")[-2]
        n = ok = side_only = nf = 0; line_cents = ok_cents = 0; piece_cents = 0
        for s in d["splits"]:
            n += 1; t = s["target"]
            if t.get("by") == "ordinance_line":
                r = line.get((str(t["fund"]), str(t["dept"]).lstrip("0"), str(t["authority"]), str(t["account"])))
            elif t.get("by") == "id": r = by.get(t["id"])
            else: r = None
            if r is None: nf += 1; continue
            line_cents += abs(r["amount_cents"])
            has = bool(kids[r["id"]])
            if s.get("mode") == "side_only" or not s.get("pieces"):
                side_only += 1
            elif has:
                ok += 1; ok_cents += abs(r["amount_cents"])
            piece_cents += sum(p.get("amount", 0) or 0 for p in s.get("pieces", []))
        res.append({"file": f"{gov}/{os.path.basename(f)}", "splits": n, "boxes_visible": ok, "side_only": side_only, "target_not_found": nf,
                    "target_lines_dollars": line_cents, "dollars_in_lines_with_boxes": ok_cents, "piece_dollars": piece_cents * 100})
    print("| File | Splits | Show as boxes | Side info only | Target not checkable here (matched by amount, or not found) | $M of lines with boxes | $M of top-level pieces |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for r in res:
        print(f"| {r['file']} | {r['splits']} | {r['boxes_visible']} | {r['side_only']} | {r['target_not_found']} | {r['dollars_in_lines_with_boxes']/1e8:,.0f} | {r['piece_dollars']/1e8:,.0f} |")
    json.dump(res, open(f"{OUT}/splits.json", "w"), indent=1)

if __name__ == "__main__":
    main()
