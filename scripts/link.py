#!/usr/bin/env python3
"""Phase 2 — join calls<->deals, build the funnel from stage history, detect the stall pile,
classify each call's bucket, and emit the verification gate + the account-naming worklist.

Plumbing: it joins on account names a MODEL produced (analysis/call_company.json) and on stage-history
rows. It never reads a transcript for meaning. Structural facts it may use: an email's domain, a
stage label's mapping, a date. Company identity and call bucket come from the model's account-naming
pass; before that pass exists, this script only ESTIMATES (and says so).
"""
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A

def canonical_stage(raw, stage_map):
    return stage_map.get(raw, None)


def build_funnel(deals, hist, cfg):
    smap = cfg.get("stage_map", {})
    order = cfg.get("stage_order", [])
    entered = collections.defaultdict(set)   # canonical stage -> set(deal keys)
    for key, rows in hist.items():
        rungs = set()
        for r in rows:
            for raw in (r.get("moved_to"), r.get("from_stage")):
                c = canonical_stage(raw, smap)
                if c:
                    rungs.add(c)
        for c in rungs:
            entered[c].add(key)
    # also seed from current stage in case a deal has no history rows
    by_id = {d["deal_id"]: d for d in deals}
    by_name = {d["deal_name"]: d for d in deals}
    for d in deals:
        if d["deal_id"] not in hist and d["deal_name"] not in hist:
            c = canonical_stage(d["stage"], smap)
            if c:
                entered[c].add(d["deal_id"])
    funnel = [{"stage": s, "deals_entered": len(entered.get(s, set()))} for s in order]
    return funnel, entered


def detect_stall(deals, entered, cfg):
    sd = cfg.get("stalled_definition", {})
    smap = cfg.get("stage_map", {})
    if sd.get("derived_from") == "config" and sd.get("stage_names"):
        raw_stalls = set(sd["stage_names"])
    else:
        # auto: the non-terminal canonical stage the most deals enter and never win
        won = entered.get("won", set())
        best, best_n = None, -1
        for s, ds in entered.items():
            if s in ("won", "lost"):
                continue
            never_won = len(ds - won)
            if never_won > best_n:
                best, best_n = s, never_won
        # map canonical back to raw labels
        raw_stalls = {raw for raw, c in smap.items() if c == best}
    stalled = [d for d in deals if d["stage"] in raw_stalls]
    return stalled, sorted(raw_stalls)


_TITLE_GENERIC = {"call", "calls", "demo", "demos", "meeting", "meet", "intro", "introduction",
                  "discussion", "discussions", "connect", "sync", "review", "weekly", "daily",
                  "cadence", "standup", "update", "catchup", "catch", "session", "team", "internal",
                  "the", "and", "for", "with", "next", "steps", "value", "proposition", "use", "case",
                  "fw", "re", "fwd", "ai", "data", "new", "old", "plan", "planning"}


def _title_external_signal_fn(deals, cfg):
    """Return f(title) -> the matched external company name (or None). Used to CATCH the bug class:
    a call whose header looks internal but whose TITLE names an external company cannot be silently
    filed internal. Signals: a distinctive CRM-account token appears in the title, OR an org-pairing
    marker ('Co || Org', 'Org <> Co', 'Co x Org') is present."""
    org_tokens = {t for t in re.findall(r"[a-z0-9]+", (cfg.get("org_name") or "").lower()) if len(t) >= 3}
    crm = {}                                  # distinctive token -> account display
    for d in deals:
        acct = d.get("account") or ""
        for t in re.findall(r"[a-z0-9]+", acct.lower()):
            if len(t) >= 4 and t not in _TITLE_GENERIC and t not in org_tokens:
                crm[t] = acct
    # org-pairing marker in a call title, e.g. "Acme || <Org>", "Acme <> <Org>", "Acme x <Org>".
    # Built from the configured org name + any aliases so it is not hard-coded to one company.
    org_words = [w for w in (org_tokens | {a.lower() for a in cfg.get("org_asr_aliases", [])}) if len(w) >= 3]
    org_alt = "|".join(re.escape(w) for w in org_words) or r"(?!x)x"  # never-matches fallback if no org name
    marker = re.compile(r"\|\||<>|(?:\bx\b|<|>)\s*(?:" + org_alt + r")|(?:" + org_alt + r")\s*(?:<>|x\b|-)", re.I)

    def f(title):
        if not title:
            return None
        tl = title.lower()
        tn = re.sub(r"[^a-z0-9]", "", tl)
        for t, acct in crm.items():
            # whole-word match, or (len>=5) substring of the despaced title (catches 'Livspace' vs CRM 'Liv Space')
            if re.search(r"\b" + re.escape(t) + r"\b", tl) or (len(t) >= 5 and t in tn):
                return acct
        if marker.search(title):
            return "(org-pairing marker)"
        return None

    return f


def main():
    wd = A.workdir()
    cfg = A.load_config(wd)
    def _opt(name, default):
        p = os.path.join(wd, "canonical", name)
        return A.read_json(p) if os.path.exists(p) else default
    calls = A.read_json(os.path.join(wd, "canonical", "transcripts.json"))
    deals = _opt("deals.json", [])          # optional: no CRM -> craft-only, no funnel
    hist = _opt("stage_history.json", {})   # optional: no stage history -> current-stage snapshot only
    notes = _opt("notes.json", {})          # optional
    cc = A.load_call_company(wd, cfg)   # applies config.call_company_overrides (partner-channel fixes)
    org_domains = cfg.get("org_domains", [])
    scope = cfg.get("scope", {})
    su = cfg.get("scoring_universe", {})
    date_from, date_to = scope.get("date_from"), scope.get("date_to")

    # account index (alias-aware: account_aliases fold spelling variants onto one key)
    acct_to_deals = collections.defaultdict(list)
    for d in deals:
        acct_to_deals[A.norm_account(d["account"], cfg)].append(d)

    funnel, entered = build_funnel(deals, hist, cfg)
    stalled, stall_raw = detect_stall(deals, entered, cfg)

    # naming policy. DEFAULT: the model reads every substantive call and decides its nature. The old
    # header-only 'internal' shortcut is NOT trusted to exclude a call from naming (it silently dropped
    # forwarded-invite external calls). An org may opt into the cheaper header-prior path, but even then
    # a title that names an external company forces naming (the title-contradiction guard below).
    ncfg = cfg.get("naming", {}) or {}
    name_all = ncfg.get("name_all_substantive", True)
    min_turns = ncfg.get("min_turns", 3)
    title_ext = _title_external_signal_fn(deals, cfg)

    # per-call structural + authoritative facts
    call_join = {}
    need_naming = []
    unaccounted = []   # substantive calls the model never read -> conservation-gate failures
    contradictions = []  # header/struct says internal, but the TITLE names an external company
    for c in calls:
        cid = c["call_id"]
        emails = c.get("header_emails", [])
        org = [e for e in emails if A.is_org_email(e, org_domains)]
        ext = [e for e in emails if e and not A.is_org_email(e, org_domains)]
        n_turns = c.get("n_turns") or 0
        in_window = (not date_from or (c["date"] and c["date"] >= date_from)) and \
                    (not date_to or (c["date"] and c["date"] <= date_to))
        info = cc.get(cid)
        if info:                       # authoritative (model read the call)
            company = info.get("company")
            bucket = info.get("bucket") or "unknown"
            status = info.get("call_status") or "live"
            quality = info.get("transcript_quality") or "fair"
            aliases = info.get("company_aliases") or []
        else:                          # STRUCTURAL ESTIMATE ONLY — never trusted to exclude from naming
            company = None
            aliases = []
            status = "live"
            quality = "fair"
            bucket = "internal" if (emails and not ext) else "unknown"
        # join company -> deals
        deal_ids = []
        if company:
            for d in acct_to_deals.get(A.norm_account(company, cfg), []):
                deal_ids.append(d["deal_id"])
            if not deal_ids:
                for al in aliases:
                    for d in acct_to_deals.get(A.norm_account(al, cfg), []):
                        deal_ids.append(d["deal_id"])
        joined = bool(deal_ids)
        # in-scope for scoring?
        in_scope = (in_window and bucket in ("external_customer", "partner")
                    and status not in su.get("exclude_call_status", [])
                    and quality not in su.get("exclude_transcript_quality", [])
                    and (joined or su.get("include_external_accounts_without_crm_deal", True)))
        title_signal = title_ext(c.get("title"))
        call_join[cid] = {"company": company, "aliases": aliases, "bucket": bucket,
                          "call_status": status, "transcript_quality": quality,
                          "deal_ids": sorted(set(deal_ids)), "joined": joined,
                          "in_window": in_window, "in_scope": bool(in_scope),
                          "date": c["date"], "title": c.get("title"),
                          "org_emails": org, "ext_emails": ext, "n_turns": n_turns,
                          "model_read": bool(info)}
        if not info:
            substantive = n_turns >= min_turns
            # name it if: policy says name everything substantive, OR it's not a header-internal guess,
            # OR the title contradicts the internal guess by naming an external company.
            if substantive and (name_all or bucket != "internal" or title_signal):
                need_naming.append(cid)
            if substantive and bucket == "internal" and title_signal:
                contradictions.append({"call_id": cid, "date": c["date"], "title": c.get("title"),
                                       "matched": title_signal})
            # ANY substantive call the model has not read is unaccounted-for until naming runs.
            if substantive:
                unaccounted.append(cid)

    # opportunity units: group by account (company) that has >=1 call OR exists in CRM
    units = collections.OrderedDict()
    # seed from CRM accounts
    for d in deals:
        if A.excluded_account(d["account"], cfg):     # advisory/partner firms dropped from the report
            continue
        k = A.norm_account(d["account"], cfg)
        units.setdefault(k, {"account": A.canonical_account(d["account"], cfg), "deal_ids": [],
                             "call_ids": [], "in_scope_call_ids": []})
        units[k]["deal_ids"].append(d["deal_id"])
    # attach calls
    for cid, j in call_join.items():
        if j["bucket"] not in ("external_customer", "partner"):
            continue
        if j["company"] and not A.excluded_account(j["company"], cfg):
            k = A.norm_account(j["company"], cfg)
            u = units.setdefault(k, {"account": A.canonical_account(j["company"], cfg), "deal_ids": [],
                                     "call_ids": [], "in_scope_call_ids": []})
            u["call_ids"].append(cid)
            if j["in_scope"]:
                u["in_scope_call_ids"].append(cid)

    opp_index = []
    for i, (k, u) in enumerate(units.items()):
        if not u["call_ids"] and not u["deal_ids"]:
            continue
        deal_objs = [d for d in deals if d["deal_id"] in set(u["deal_ids"])]
        stages = [d["stage"] for d in deal_objs]
        outcome = ("won" if any(cfg["stage_map"].get(s) == "won" for s in stages) else
                   "lost" if stages and all(cfg["stage_map"].get(s) == "lost" for s in stages) else
                   "stalled" if any(s in stall_raw for s in stages) else "open")
        opp_index.append({
            "unit_index": i, "account": u["account"], "norm": k,
            "deal_ids": sorted(set(u["deal_ids"])), "call_ids": sorted(set(u["call_ids"])),
            "in_scope_call_ids": sorted(set(u["in_scope_call_ids"])),
            "call_count": len(set(u["call_ids"])),
            "in_scope_call_count": len(set(u["in_scope_call_ids"])),
            "outcome": outcome,
            "arr": max([_num(d["arr"]) for d in deal_objs], default=0),
        })

    # ---- CRM <-> corpus reconciliation: which CRM accounts have NO call in the corpus ----
    covered = set()
    for j in call_join.values():
        if j["company"]:
            covered.add(A.norm_account(j["company"], cfg))
        for did in j["deal_ids"]:
            covered.add(did)
    crm_no_call = []
    for d in deals:
        if A.norm_account(d["account"], cfg) in covered or d["deal_id"] in covered:
            continue
        crm_no_call.append({"deal_id": d["deal_id"], "account": d["account"],
                            "deal_name": d.get("deal_name"), "owner": d.get("owner"),
                            "stage": d.get("stage"), "arr": _num(d.get("arr"))})
    crm_no_call.sort(key=lambda x: -x["arr"])

    A.write_json(os.path.join(wd, "analysis", "call_join.json"), call_join)
    A.write_json(os.path.join(wd, "analysis", "opp_index.json"), opp_index)
    A.write_json(os.path.join(wd, "analysis", "funnel.json"),
                 {"funnel": funnel, "stall_raw_stages": stall_raw,
                  "stall_pile_size": len(stalled)})
    A.write_json(os.path.join(wd, "analysis", "naming_worklist.json"), need_naming)
    A.write_json(os.path.join(wd, "analysis", "coverage_gaps.json"), {
        "unaccounted_calls": unaccounted,                         # substantive calls the model never read
        "title_contradicts_internal": contradictions,            # header says internal, title names a customer
        "crm_accounts_without_call": crm_no_call,                 # deals with zero corpus call (export gap OR off-channel)
    })

    # ---- verification gate ----
    joined_calls = sum(1 for j in call_join.values() if j["joined"])
    scored_calls = sum(1 for j in call_join.values() if j["in_scope"])
    ext_calls = sum(1 for j in call_join.values() if j["bucket"] in ("external_customer", "partner"))
    internal_calls = sum(1 for j in call_join.values() if j["bucket"] == "internal")
    unknown_calls = sum(1 for j in call_join.values() if j["bucket"] == "unknown")
    units_with_calls = sum(1 for u in opp_index if u["call_count"] > 0)
    units_scored = sum(1 for u in opp_index if u["in_scope_call_count"] > 0)
    won = len([d for d in deals if cfg["stage_map"].get(d["stage"]) == "won"])
    demo_deals = len(entered.get("tailored_demo", set()))
    # exact 3-way partition: read + (unread & trivial) + (unread & substantive=unaccounted) = ingested
    n_read = sum(1 for j in call_join.values() if j["model_read"])
    trivial = sum(1 for j in call_join.values() if not j["model_read"] and (j["n_turns"] or 0) < min_turns)

    print(f"\n================ VERIFICATION GATE — {cfg.get('org_name')} ================")
    print(f"  transcripts ingested............ {len(calls)}")
    print(f"  deals parsed.................... {len(deals)}   (with stage history: {len(hist)})")
    print(f"  closed-won deals................ {won}    demo-stage: {demo_deals}    stall ('{','.join(stall_raw)}'): {len(stalled)}")
    print(f"  --- CONSERVATION LEDGER (every ingested call must be accounted for) ---")
    print(f"    model-read (account-named).... {n_read}")
    print(f"      external/partner............ {ext_calls}")
    print(f"      internal (context only)..... {internal_calls}")
    print(f"      unknown (model unsure)...... {unknown_calls}")
    print(f"    trivial (< {min_turns} turns, skipped). {trivial}")
    print(f"    UNACCOUNTED (substantive, NOT read) {len(unaccounted)}")
    print(f"    ledger: {n_read} read + {trivial} trivial + {len(unaccounted)} unaccounted = "
          f"{n_read + trivial + len(unaccounted)} / {len(calls)} ingested")
    print(f"  --- joins ---")
    print(f"    calls joined to a CRM deal.... {joined_calls}")
    print(f"    IN-SCOPE scored calls......... {scored_calls}")
    print(f"    units w/ calls / in scope..... {units_with_calls} / {units_scored}")
    print(f"  --- coverage gaps (analysis/coverage_gaps.json) ---")
    print(f"    CRM deals with ZERO corpus call {len(crm_no_call)}  (export-missed OR off-channel)")
    print(f"    title-says-external-but-internal {len(contradictions)}  (the Livspace bug signature)")
    if unaccounted:
        print("\n  ✗✗✗ GATE FAILED — {} substantive call(s) were NEVER read by the namer.".format(len(unaccounted)))
        print("      A structural shortcut must not silently drop calls. Run the namer, then re-link:")
        print("        python3 scripts/name_run.py            # names analysis/naming_worklist.json")
        print("        python3 scripts/link.py                # re-checks the ledger")
        print("      worklist: analysis/naming_worklist.json")
    else:
        print("\n  ✓ ledger balances — every substantive call was read by the namer.")
    if contradictions:
        print(f"  ⚠ {len(contradictions)} call(s) had an external company in the title but an internal header;")
        print( "    they are forced into the naming worklist (never trusted as internal).")
    print("=========================================================================\n")
    return 1 if unaccounted else 0


def _num(x):
    try:
        return float(str(x).replace(",", "") or 0)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    sys.exit(main())
