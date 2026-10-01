"""Independent check of data/budget.db after all three builders have run.

Re-checks everything from the database itself (not the builders' in-memory trees):
  * each government's root equals the official printed total, to the cent
  * every parent equals the sum of its children, no orphans
  * every node has a basis and a source
  * every leaf of $10M or more (except adjustments) has a "why can't I go deeper" sentence
Exits 1 on any failure.
"""
import os
import sqlite3
import sys

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
sys.exit(1 if fail else 0)
