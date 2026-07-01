#!/usr/bin/env python3
"""Collect + verify the judgment outputs, regardless of engine. In host-agent mode the host writes each
subagent's JSON into analysis/call_out/, analysis/postmortem/, analysis/adherence_calls/. In API mode the
driver scripts write the same files. This script then:

  1. validates the shapes of call_out/ and postmortem/ files (drops malformed, reports them),
  2. enforces the read-every-call invariant (scored calls vs in-scope transcripts), and
  3. rolls the per-call adherence checks up into analysis/adherence.json.

Pure plumbing: it never scores anything. Run it after scoring + post-mortems + adherence, before aggregate.py.

  python3 scripts/merge_scores.py --workdir <dir>
"""
import os, sys, glob, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A

ADHERENCE_RULES = {
    "R1": "explainer-quote grounding: an evidence quote must be the explainer's actual words from the transcript",
    "R2": "read the whole turn: do not floor a dimension to 1 when the explainer gave a substantive reply",
    "R3": "scale anchoring: no defaulting to 3; a 4 or 5 must land, a 1 or 2 must reflect a real miss",
    "R4": "craft versus outcome firewall: score the move, not the deal result or the technical win",
    "R5": "earned on the call: technical discovery, accuracy, substance, and POC scoping credited only from what the explainer did on the call",
    "R6": "demo So-What: a feature-dump (capabilities shown with no linked pain and no stated impact) must not be scored as high demo craft",
    "R7": "anti-slop: no buzzwords or stray dashes in authored prose",
}


def _valid_call_out(o):
    return isinstance(o, dict) and o.get("call_id") and isinstance(o.get("reps"), list)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.environ.get("AUDIT_WORKDIR", ""))
    args = ap.parse_args()
    wd = args.workdir or A.workdir()
    an = os.path.join(wd, "analysis")

    # 0. collect naming records (host-agent mode) into call_company.json, if present
    nout = os.path.join(an, "naming_out")
    if os.path.isdir(nout):
        FIELDS = ("company", "company_aliases", "bucket", "call_status", "transcript_quality",
                  "call_phase", "is_sales_relevant", "se_stage", "primary_external_participants",
                  "org_participants", "technical_explainers", "one_line")
        ccp = os.path.join(an, "call_company.json")
        cc = A.read_json(ccp) if os.path.exists(ccp) else {}
        if not isinstance(cc, dict):
            cc = {}
        nmerged = 0
        for fp in glob.glob(os.path.join(nout, "*.json")):
            try:
                r = A.read_json(fp)
            except Exception:
                continue
            cid = r.get("call_id") or os.path.basename(fp)[:-5]
            rec = {k: r.get(k) for k in FIELDS if k in r}
            rec["call_id"] = cid
            cc[cid] = {**(cc.get(cid) or {}), **rec}
            nmerged += 1
        A.write_json(ccp, cc)
        print(f"== merge_scores: collected {nmerged} naming records -> analysis/call_company.json")

    # 1. validate call_out
    co_ok, co_bad = 0, []
    for fp in glob.glob(os.path.join(an, "call_out", "call_*.json")):
        try:
            o = A.read_json(fp)
            if _valid_call_out(o):
                co_ok += 1
            else:
                co_bad.append(os.path.basename(fp))
        except Exception:
            co_bad.append(os.path.basename(fp))

    # 2. validate postmortem
    pm_ok, pm_bad = 0, []
    for fp in glob.glob(os.path.join(an, "postmortem", "deal_*.json")):
        try:
            o = A.read_json(fp)
            if isinstance(o, dict) and o.get("unit_index") is not None:
                pm_ok += 1
            else:
                pm_bad.append(os.path.basename(fp))
        except Exception:
            pm_bad.append(os.path.basename(fp))

    # 3. read-every-call invariant: in-scope transcripts vs scored calls
    gap = None
    opp_path = os.path.join(an, "opp_index.json")
    if os.path.exists(opp_path):
        opp = A.read_json(opp_path)
        in_scope = set()
        for u in opp:
            for cid in u.get("in_scope_call_ids", []):
                in_scope.add(cid)
        scored = {os.path.basename(f)[5:-5] for f in glob.glob(os.path.join(an, "call_out", "call_*.json"))}
        missing = in_scope - scored
        gap = {"in_scope": len(in_scope), "scored": len(in_scope & scored), "missing": sorted(missing)[:50]}

    # 4. adherence aggregate
    checks = []
    for fp in glob.glob(os.path.join(an, "adherence_calls", "check_*.json")):
        try:
            checks.append(A.read_json(fp))
        except Exception:
            pass
    if checks:
        by_rule, verdicts, deltas, majors, rep_n = {}, {"pass": 0, "minor": 0, "major": 0}, [], [], 0
        for ch in checks:
            for rp in ch.get("reps", []):
                rep_n += 1
                v = rp.get("verdict", "pass")
                verdicts[v] = verdicts.get(v, 0) + 1
                for vio in (rp.get("violations") or []):
                    by_rule[vio.get("rule", "?")] = by_rule.get(vio.get("rule", "?"), 0) + 1
                for rs in (rp.get("rescore") or []):
                    m, c = rs.get("maker"), rs.get("checker")
                    if isinstance(m, (int, float)) and isinstance(c, (int, float)):
                        deltas.append(abs(m - c))
                if v == "major":
                    top = (rp.get("violations") or [{}])[0]
                    majors.append({"call_id": ch.get("call_id"), "account": ch.get("account"),
                                   "rep": rp.get("rep_name"), "reason": f"{top.get('rule','')}: {top.get('detail','')}"[:160]})
        agg = {
            "checker_model": os.environ.get("ADHERENCE_CHECKER", "independent seat"),
            "maker_model": os.environ.get("ADHERENCE_MAKER", "scorer"),
            "calls_audited": len(checks), "reps_audited": rep_n, "verdicts": verdicts,
            "pass_rate": round(verdicts["pass"] / rep_n, 3) if rep_n else None,
            "violations_by_rule": dict(sorted(by_rule.items())),
            "mean_abs_rescore_delta": round(sum(deltas) / len(deltas), 2) if deltas else None,
            "rescore_n": len(deltas), "majors": majors[:40],
            "rules": {k: v[:90] for k, v in ADHERENCE_RULES.items()},
        }
        A.write_json(os.path.join(an, "adherence.json"), agg)

    # report
    print(f"== merge_scores: call_out {co_ok} valid" + (f", {len(co_bad)} malformed: {co_bad[:8]}" if co_bad else ""))
    print(f"   postmortem {pm_ok} valid" + (f", {len(pm_bad)} malformed: {pm_bad[:8]}" if pm_bad else ""))
    if gap is not None:
        status = "OK" if not gap["missing"] else f"GAP: {len(gap['missing'])} in-scope calls NOT scored"
        print(f"   read-every-call: {gap['scored']}/{gap['in_scope']} in-scope transcripts scored -> {status}")
        if gap["missing"]:
            print(f"   missing call_ids (first 50): {gap['missing']}")
    if checks:
        print(f"   adherence: {len(checks)} calls audited -> analysis/adherence.json")


if __name__ == "__main__":
    main()
