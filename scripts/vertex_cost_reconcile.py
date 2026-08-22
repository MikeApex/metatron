#!/usr/bin/env python3
"""
scripts/vertex_cost_reconcile.py — answer the two open cache-cost questions from
the BigQuery billing export, and reconcile the bill against spend_guard.

Step 5 of archive/plans/vertex_cache_cost_control_2026-08-20_plan.md. The export
was enabled 2026-08-21 and is NOT retroactive, so this returns nothing until the
first rows land (typically within 24h of enabling).

Two questions it settles, neither of which the SKU catalogue can answer, because
the catalogue lists rates and this lists what was actually charged:

  1. Which SKU does cache CREATION meter on? The catalogue has exactly three
     candidates per model — "Text Input - Predictions" ($2.00/M on Pro),
     "Text Input Caching" ($0.20/M), and "Text Input Caching Storage" (per hour).
     A controlled probe on 2026-08-20 proved creation is metered (12,001 tokens
     billed as input against zero generate calls); it could not say at which rate.
     The answer decides whether a burst that creates one cache costs $0.015 or
     $0.0015 — a 10x swing on the only figure the caching decision turns on.

  2. Does the TTL refresh (cachedContents.patch) meter anything? It should not
     re-ingest tokens. "Should not" is what the creation probe existed to test.
     If it does, the sliding TTL's refresh cadence becomes a cost parameter
     rather than a correctness one.

Run on the Mac (ADC already has BigQuery access):
    python3 scripts/vertex_cost_reconcile.py                # last 3 days
    python3 scripts/vertex_cost_reconcile.py --days 7
"""

from __future__ import annotations

import argparse
import subprocess
import sys

PROJECT = "metatron-ai-499810"
DATASET = "billing_export"


def _bq(sql: str) -> str:
    out = subprocess.run(
        ["bq", "query", "--use_legacy_sql=false", "--format=prettyjson", "--max_rows=500", sql],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(f"query failed:\n{sql}\n{out.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return out.stdout


def _find_table() -> str | None:
    out = subprocess.run(["bq", "ls", "--format=json", DATASET], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    import json
    for t in json.loads(out.stdout or "[]"):
        tid = t["tableReference"]["tableId"]
        if tid.startswith("gcp_billing_export"):
            return f"{PROJECT}.{DATASET}.{tid}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    args = ap.parse_args()

    table = _find_table()
    if table is None:
        print(f"No gcp_billing_export table in {DATASET} yet.")
        print("The export is not retroactive and the first rows usually land within 24h of")
        print("enabling it. Nothing is wrong — re-run tomorrow.")
        return 0

    print(f"table: {table}\n")

    # Every Vertex SKU that carries a cost, most expensive first. The SKU
    # DESCRIPTION is the answer to question 1: if creation lands on
    # "Text Input - Predictions" it is the standard rate; if it lands on
    # "Text Input Caching" it is the discounted one.
    print("=== Vertex AI cost by SKU ===")
    print(_bq(f"""
        SELECT
          sku.description AS sku,
          ROUND(SUM(cost), 4)  AS usd,
          ROUND(SUM(usage.amount), 0) AS usage_amount,
          ANY_VALUE(usage.unit) AS unit,
          COUNT(*) AS row_count
        FROM `{table}`
        WHERE service.description = 'Vertex AI'
          AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {args.days} DAY)
        GROUP BY sku
        HAVING usd > 0 OR usage_amount > 0
        ORDER BY usd DESC
    """))

    # Question 2: a storage SKU with usage but no matching caching-input SKU
    # movement on a refresh-heavy day means patch does not re-ingest.
    print("=== Cache SKUs only, by day ===")
    print(_bq(f"""
        SELECT
          DATE(usage_start_time) AS day,
          sku.description AS sku,
          ROUND(SUM(cost), 4) AS usd,
          ROUND(SUM(usage.amount), 0) AS usage_amount,
          ANY_VALUE(usage.unit) AS unit
        FROM `{table}`
        WHERE service.description = 'Vertex AI'
          AND LOWER(sku.description) LIKE '%caching%'
          AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {args.days} DAY)
        GROUP BY day, sku
        ORDER BY day DESC, usd DESC
    """))

    print("=== Daily Vertex total — compare against data/diagnostics/spend_YYYY-MM-DD.json ===")
    print(_bq(f"""
        SELECT DATE(usage_start_time) AS day, ROUND(SUM(cost), 4) AS usd
        FROM `{table}`
        WHERE service.description = 'Vertex AI'
          AND usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {args.days} DAY)
        GROUP BY day ORDER BY day DESC
    """))
    print("Pass condition for the plan's closing test: billed / estimated under 1.2x,")
    print("down from ~2.3x on 08-19. Both hosts count — sum the Mac's and the VM's state files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
