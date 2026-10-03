"""Independent check of data/budget.db after all three builders have run.

Re-checks everything from the database itself (not the builders' in-memory trees):
  * each government's root equals the official printed total, to the cent
  * every parent equals the sum of its children, no orphans
  * every node has a basis and a source
  * every leaf of $10M or more (except adjustments) has a "why can't I go deeper" sentence
Exits 1 on any failure.
"""
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
from payee import ALLOWED_INDIVIDUAL_DESCRIPTIONS  # noqa: E402

DB = os.path.join(os.path.dirname(__file__), "..", "data", "budget.db")
OFFICIAL = {"city": 16_842_553_003_00, "cps": 10_253_327_463_68, "parks": 637_580_350_00}

con = sqlite3.connect(DB)
q = lambda s, *a: con.execute(s, a).fetchall()  # noqa: E731
fail = 0
for gov, exp in OFFICIAL.items():
    root = q("select amount_cents from nodes where id=?", gov)
    root = root[0][0] if root else None
    bad = q("""select count(*) from nodes p join (select parent_id, sum(amount_cents) s from nodes where gov=?
               group by parent_id) c on c.parent_id=p.id where p.amount_cents!=c.s""", gov)[0][0]
    orph = q("""select count(*) from nodes n where gov=? and parent_id is not null and
                not exists (select 1 from nodes p where p.id=n.parent_id)""", gov)[0][0]
    nosrc = q("select count(*) from nodes where gov=? and (source is null or basis is null)", gov)[0][0]
    nowhy = q("""select count(*) from nodes where gov=? and is_leaf=1 and abs(amount_cents)>=1000000000
                 and coalesce(why_cant_go_deeper,'')='' and basis!='adjustment'""", gov)[0][0]
    n = q("select count(*) from nodes where gov=?", gov)[0][0]
    ok = root == exp and bad == 0 and orph == 0 and nosrc == 0 and nowhy == 0
    fail += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {gov:6} {n:>7,} boxes  total ${root/100 if root else 0:>18,.2f}  "
          f"(official ${exp/100:,.2f})  bad sums {bad}  orphans {orph}  no source {nosrc}  big leaves w/o why {nowhy}")

# Privacy: payments to hidden individuals may carry only a neutral label as their description, and an
# "individuals" box may carry only the standard note (no names, roles or contract text), and has no children.
HIDDEN = "Individual (name hidden)"
bad_desc = n_rows = 0
for (extra,) in q("select extra from side_info where extra like '%name hidden%'"):
    for it in (json.loads(extra or "{}").get("items") or []):
        if isinstance(it, dict) and (it.get("is_individual") or it.get("vendor") == HIDDEN) and "description" in it:
            n_rows += 1
            bad_desc += it["description"] not in ALLOWED_INDIVIDUAL_DESCRIPTIONS
NOTE_OK = re.compile(r"^\d+ payments to people, refunds, small grants or sole practitioners\. Names are hidden to protect privacy\.( Matched to this line using how the City coded this contract's 2025 invoices\.)?$")
NAME_OK = re.compile(r"^(Individual \(name hidden\)|Payments to \d+ individuals \(names hidden\))$")
bad_box = sum(1 for _id, nm, note in q("select id, name, note from nodes where kind='individuals'")
              if not (NAME_OK.match(nm or "") and NOTE_OK.match(note or "")))
bad_box += q("select count(*) from nodes c join nodes p on c.parent_id=p.id where p.kind='individuals'")[0][0]
ok = bad_desc == 0 and bad_box == 0
fail += not ok
print(f"{'OK  ' if ok else 'FAIL'} privacy: {n_rows:,} individual payment rows with a description, {bad_desc} not a neutral label; "
      f"individuals boxes with a non-standard name, note or children: {bad_box}")
sys.exit(1 if fail else 0)
