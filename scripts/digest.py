#!/usr/bin/env python3
"""Fold the per-call run into analysis/council_digest.json, the single file each council seat reads.
Sources the NEW per-call aggregate (analysis/report_data.json): org floor/strong dims, stall-archetype
clusters, MEDDIC reality, the maker-checker adherence, per-rep craft spread (with each rep's recurring
failure + signature), and a curated set of the highest-stakes deal post-mortems.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A


def main():
    wd = A.workdir()
    cfg = A.load_config(wd)
    d = A.read_json(os.path.join(wd, "analysis", "report_data.json"))
    org, reps, deals, DN = d["org"], d["reps"], d["deals"], d["dim_names"]

    rep_spread = [{"name": r["name"], "archetype": r["archetype"], "craft": r["craft"], "bar": r["bar"],
                   "vs_bar": r.get("vs_bar"), "n_calls": r["n_calls"], "rank_eligible": r["rank_eligible"],
                   "recurring_failure": (r.get("recurring") or {}).get("name"),
                   "signature": (r.get("signature") or {}).get("name"),
                   "outcomes": r["outcomes"]} for r in reps]

    # highest-stakes post-mortems first (stalled, then lost, then the rest), by ARR
    rank = {"stalled": 0, "open": 1, "lost": 2, "won": 3}
    ds = sorted(deals, key=lambda x: (rank.get(x.get("outcome"), 4), -(float(x.get("arr") or 0))))
    deal_summaries = []
    for dl in ds[:32]:
        pm = dl.get("postmortem") or {}
        deal_summaries.append({
            "account": dl.get("account"), "outcome": dl.get("outcome"), "arr": dl.get("arr"),
            "headline": pm.get("headline"), "why_hold": pm.get("why_hold"),
            "stall_archetype": pm.get("stall_archetype"), "one_change": pm.get("one_change")})

    digest = {
        "org_name": cfg.get("org_name"), "stall_label": org.get("stall_label"),
        "funnel": org.get("funnel"),
        "floor_dims": [f"{x['name']} {x['avg']}" for x in org.get("floor_dims", [])],
        "strong_dims": [f"{x['name']} {x['avg']}" for x in org.get("strong_dims", [])],
        "org_dim_avgs": {DN.get(k, k): v for k, v in (org.get("dim_avgs") or {}).items() if v is not None},
        "stall_archetype_counts": {a["key"]: a["n"] for a in org.get("stall_archetypes", [])},
        "meddic_reality": org.get("meddic_reality"),
        "technical_win": org.get("technical_win"), "demo": org.get("demo"), "quarters": org.get("quarters"),
        "adherence": {k: org.get("adherence", {}).get(k) for k in ("pass_rate", "verdicts", "violations_by_rule", "mean_abs_rescore_delta")} if org.get("adherence") else None,
        "n_calls_scored": org.get("n_calls_scored"), "n_reps": org.get("n_reps"), "n_ranked": org.get("n_reps_ranked"),
        "rep_spread": rep_spread,
        "deal_summaries": deal_summaries,
        "deal_summary_note": f"showing {len(deal_summaries)} of {len(deals)} deals, highest-stakes first",
    }
    A.write_json(os.path.join(wd, "analysis", "council_digest.json"), digest)
    print(f"== digest: {len(rep_spread)} reps, {len(deal_summaries)}/{len(deals)} deals -> council_digest.json")


if __name__ == "__main__":
    main()
