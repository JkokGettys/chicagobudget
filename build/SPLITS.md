# Split files: how agents add detail to the tree

Detail is added as JSON files in `data/splits/<gov>/*.json`. The tree builders apply every file there
(after their own built-in splits) with `treelib.apply_split_file()`. Agents should **write split files,
not edit the builders**, so several agents can add detail at once.

```json
{
  "meta": {"author": "agent label", "description": "what this file adds", "built_by": "scripts/xxx.py"},
  "splits": [
    {
      "target": {"by": "ordinance_line", "fund": "0100", "dept": "57", "authority": "1005", "account": "0020"},
      "expect_amount": 200000000,
      "mode": "budget_split",
      "pieces": [
        {"name": "Patrol overtime", "amount": 120000000, "basis": "gov_estimate",
         "source": {"doc": "2026 Budget Recommendations", "url": "...", "page": 412},
         "count": null, "unit_amount": null, "unit_label": null,
         "why": "sentence, required if amount >= $10M and there are no children",
         "children": [ {"name": "...", "amount": 1}, "..." ]}
      ],
      "residual": {"name": "Other overtime not itemised", "why": "..."},
      "note": "optional note shown on the line",
      "side": [ {"kind": "...", "label": "...", "amount": 123, "period": "2025", "basis": "actual", "source": {}} ]
    }
  ]
}
```

## Rules (the builder enforces them, and a bad split is skipped and logged, never forced)

- **Amounts are dollars** (numbers, cents allowed). The builder converts them to integer cents.
- **Target** (the box to split). City: `{"by": "ordinance_line", "fund", "dept", "authority", "account"}`
  (codes as in dataset 6694-f78c, dept without leading zeros), or `{"by": "id", "id": "<node id>"}`.
  CPS and Parks: `{"by": "id", "id": ...}` or `{"by": "match", "contains": [..], "amount": ...}`.
  The target must be a leaf (not already split). `expect_amount` must equal the line, or the split is skipped.
- **mode `budget_split`** (default): the pieces must add up to no more than the line. Any remainder becomes a
  visible "Other / not itemised" box (`residual` names it). Never scale numbers to fit.
- **mode `paid_to_date`**: pieces are payments actually made this year (basis `paid_to_date`). The rest of the
  line becomes "Budgeted but not spent yet". If payments exceed the line, a negative
  "Already spent more than the budget" box keeps the sum right.
- **basis per piece**: `tied` (exact), `gov_estimate` (an estimate the government published, which is preferred
  over our own estimates), `proxy` (our estimate: say exactly how in `note` and `source`), `paid_to_date`.
  Prefer government numbers. Only use `proxy` when nothing official exists, and label it clearly.
- **Nested `children`** must also fit inside their piece (a remainder becomes "Other / not itemised").
- **Every leaf of $10M or more needs `why`.** One plain sentence a 13-year-old can read.
- **No names of private individuals.** Business names are fine. Hide people with "Individual (name hidden)".
- **Side info** (`side`) is facts that are not added into amounts (prior-year actuals, counts, projections).
