# Phase 21 sizing (counts only, before any score)

Run `noema-p12-20260930-154851`, `scripts/count-phase21.py`, torn down and
verified. Unconnected (work, area) pairs at each cutoff, by span threshold;
important jump = at least 5 area papers cite the work in the 10 years after
the cutoff.

| span ≥ (bits) | 2005: pairs | crossed | important | 2015: pairs | crossed | important |
|---|---:|---:|---:|---:|---:|---:|
| 4.65 (arrival 90th pct) | 276,425 | 12,590 | 888 | 1,740,036 | 11,734 | 88 |
| 5.00 | 234,557 | 8,802 | 605 | 1,442,529 | 7,267 | 53 |
| 5.84 (arrival 99th pct) | 146,938 | 3,569 | **229** | 813,798 | 2,013 | 11 |
| 7.00 | 59,848 | 533 | 9 | 296,353 | 262 | 1 |

(Full grid in `count21.json`.)

## Data problem found

The 2015 column is far lower than 2005 despite eight times as many pairs.
Reference coverage in the Phase 11 data collapses after 2021: the share of
papers with no references is 16–25% up to 2012, 32–46% in 2015–2021, then
79% (2022), 83%, 88%, 95% (2025). Any outcome window reaching past 2021 is
undercounted. This affects Phase 18's peek, Phase 20's forward test (H2) and
its 2025 live list. Phase 13's outcome window (2007–2021) and every
learn-window result (to 2015) are unaffected, though coverage already falls
from 2010.
