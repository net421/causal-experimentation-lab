# Data dictionary

| Field | Type | Meaning |
|---|---|---|
| `unit_id` | string | Synthetic distribution-center identifier |
| `region` | category | North, south, east, or west stratum descriptor |
| `capacity_index` | float | Pre-assignment operating-capacity index |
| `baseline_gross_margin` | float | Gross margin in the eight weeks before assignment, USD |
| `baseline_stockout_rate` | float | Stockout fraction in the eight weeks before assignment |
| `treatment` | integer | 1 for priority replenishment, 0 for business as usual |
| `post_gross_margin` | float | Gross margin in the eight weeks after assignment, USD |
| `post_stockout_rate` | float | Stockout fraction in the eight weeks after assignment |

All rows are generated from a seeded synthetic data-generating process. They contain no real company, facility, customer, or transaction data.

