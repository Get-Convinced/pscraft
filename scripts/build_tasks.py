#!/usr/bin/env python3
"""Deterministic task-prep for the judgment phases that are not the per-call scorer (that has its own
driver, score_calls.py). Emits filled prompts to analysis/tasks/<phase>/ so the host can run one
subagent per task (host-agent mode), or so an API driver can loop them. Pure plumbing: no model calls.

  python3 scripts/build_tasks.py doc-ingest    --workdir <dir>   # POC/MAP/security/design docs -> canonical
  python3 scripts/build_tasks.py technical_win --workdir <dir>   # one per deal: infer the Technical Win
  python3 scripts/build_tasks.py postmortem    --workdir <dir>   # one per deal
  python3 scripts/build_tasks.py adherence     --workdir <dir> [--sample 24]
  python3 scripts/build_tasks.py naming        --workdir <dir>

Each task file is {key, out_path, prompt}. The host runs the prompt and writes the JSON to out_path,
echoing the task's identity fields (unit_index, account) into the output where the shape needs them.
"""
import os, re, sys, glob, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lib import audit as A
import extract_docs

PER_CALL = 8000
TOTAL = 24000
TXT_CAP = 16000


def load_template(name):
    t = open(os.path.join(SKILL, "prompts", name), encoding="utf-8").read()
    return re.sub(r"^<!--.*?-->\s*", "", t, flags=re.S)


def fill(t, **kw):
    for k, v in kw.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def _poc_by_acct(wd, cfg):
    out = {}
    p = os.path.join(wd, "canonical", "poc_plans.json")
    if os.path.exists(p):
        for rec in A.read_json(p):
            out.setdefault(A.norm_account(rec.get("account") or "", cfg), []).append(rec)
    return out


def _poc_criteria_text(account, poc_by_acct, cfg):
    lines = []
    for rec in poc_by_acct.get(A.norm_account(account or "", cfg), []):
        for c in (rec.get("criteria") or []):
            t = (c.get("text") or "").strip()
            if not t:
                continue
            mt = " ".join(x for x in [c.get("metric"), c.get("target")] if x)
            lines.append(f"- {t}" + (f" [{mt}]" if mt.strip() else ""))
    return "\n".join(lines[:20]) or "(no POC criteria doc)"


def _deal_transcripts(u, calls, cc):
    cids = sorted(u.get("in_scope_call_ids", []), key=lambda c: calls.get(c, {}).get("date") or "")
    blocks, used = [], 0
    for cid in cids:
        c = calls.get(cid)
        if not c:
            continue
        t = A.transcript_text(c, max_chars=PER_CALL)
        if used + len(t) > TOTAL:
            t = t[:max(0, TOTAL - used)]
        blocks.append(f"\n== CALL {c.get('date')} | {c.get('title')} ==\n{t}"); used += len(t)
        if used >= TOTAL:
            break
    return "".join(blocks)


def _callout_by_unit(wd):
    by = {}
    for fp in glob.glob(os.path.join(wd, "analysis", "call_out", "call_*.json")):
        co = A.read_json(fp)
        by.setdefault(co.get("unit_index"), []).append(co)
    return by


def naming_tasks(wd, cfg):
    calls = {c["call_id"]: c for c in A.read_json(os.path.join(wd, "canonical", "transcripts.json"))}
    wl_path = os.path.join(wd, "analysis", "naming_worklist.json")
    targets = A.read_json(wl_path) if os.path.exists(wl_path) else list(calls)
    org = cfg.get("org_name"); oneliner = cfg.get("product_oneliner", "")
    domains = ", ".join(cfg.get("org_domains", [])) or "(none provided)"
    kbp = os.path.join(wd, "company_context.md")
    kb = open(kbp, encoding="utf-8").read()[:4000] if os.path.exists(kbp) else ""
    tmpl = load_template("account_naming.md")
    out = os.path.join(wd, "analysis", "tasks", "naming"); os.makedirs(out, exist_ok=True)
    n = 0
    for cid in targets:
        c = calls.get(cid)
        if not c:
            continue
        prompt = fill(tmpl, ORG=org, ONELINER=oneliner, ORG_DOMAINS=domains, COMPANY_CONTEXT=kb,
                      CALL_ID=cid, TRANSCRIPT=A.transcript_text(c, max_chars=TXT_CAP))
        A.write_json(os.path.join(out, f"{cid}.json"),
                     {"call_id": cid, "out_path": f"analysis/naming_out/{cid}.json", "prompt": prompt})
        n += 1
    print(f"== emitted {n} naming tasks -> {out}")


def doc_ingest_tasks(wd, cfg):
    """One poc_ingest task per artifact document under the configured raw doc dirs. Extracts the text
    with extract_docs, emits a task that writes canonical structure to analysis/<kind>_out/, which
    normalize.py's collect_artifacts folds into canonical/."""
    ing = cfg.get("ingest", {}) or {}
    kinds = {"poc": ing.get("poc_docs_dir", "raw/poc"), "map": ing.get("map_docs_dir", "raw/map"),
             "security": ing.get("security_qs_dir", "raw/security"), "design": ing.get("solution_design_dir", "raw/design")}
    tmpl = load_template("poc_ingest.md")
    total = 0
    for kind, rel in kinds.items():
        d = rel if os.path.isabs(rel) else os.path.join(wd, rel)
        if not os.path.isdir(d):
            continue
        out = os.path.join(wd, "analysis", "tasks", f"docing_{kind}"); os.makedirs(out, exist_ok=True)
        for path in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
            if not os.path.isfile(path):
                continue
            text, note = extract_docs.extract_one(path)
            body = text if text else note
            slug = A.slug(os.path.splitext(os.path.basename(path))[0])
            prompt = fill(tmpl, ORG_OPTIONAL="", DOC_KIND=kind, DEAL_HINT="(unknown; infer the account from the document)",
                          SOURCE_DOC=os.path.basename(path), DOC_TEXT=(body or "")[:TXT_CAP])
            A.write_json(os.path.join(out, f"{slug}.json"),
                         {"kind": kind, "source_doc": os.path.basename(path),
                          "out_path": f"analysis/{kind}_out/{slug}.json", "prompt": prompt})
            total += 1
    print(f"== emitted {total} doc-ingest tasks. Run them, then rerun normalize.py to collect into canonical/.")


def technical_win_tasks(wd, cfg):
    org = cfg.get("org_name")
    calls = {c["call_id"]: c for c in A.read_json(os.path.join(wd, "canonical", "transcripts.json"))}
    cc = A.load_call_company(wd, cfg)
    opp = A.read_json(os.path.join(wd, "analysis", "opp_index.json"))
    deals = {d["deal_id"]: d for d in A.read_json(os.path.join(wd, "canonical", "deals.json"))} if os.path.exists(os.path.join(wd, "canonical", "deals.json")) else {}
    sep = {}
    sepp = os.path.join(wd, "canonical", "se_platform.json")
    if os.path.exists(sepp):
        for r in A.read_json(sepp):
            sep.setdefault(A.norm_account(r.get("account") or "", cfg), []).append(r)
    poc_by = _poc_by_acct(wd, cfg)
    co_by_unit = _callout_by_unit(wd)
    tmpl = load_template("technical_win.md")
    out = os.path.join(wd, "analysis", "tasks", "technical_win"); os.makedirs(out, exist_ok=True)
    n = 0
    for u in opp:
        if not u.get("in_scope_call_ids"):
            continue
        acct = u.get("account")
        gaps = []
        for co in co_by_unit.get(u["unit_index"], []):
            for rp in co.get("reps", []):
                for g in (rp.get("gap_contributions") or []):
                    gaps.append(f"[{co.get('date')}] {g.get('gap')} -> {g.get('status')}")
        deal_objs = [deals[d] for d in u.get("deal_ids", []) if d in deals]
        flag = next((d.get("technical_win_flag") for d in deal_objs if d.get("technical_win_flag")), "")
        for r in sep.get(A.norm_account(acct or "", cfg), []):
            flag = flag or r.get("technical_win_flag")
        biz = f"outcome: {u.get('outcome')}; arr: {u.get('arr')}; stage: {', '.join(d.get('stage','') for d in deal_objs) or 'unknown'}"
        prompt = fill(tmpl, ORG=org, ACCOUNT=acct,
                      POC_CRITERIA=_poc_criteria_text(acct, poc_by, cfg),
                      PLATFORM_FLAG=(f"flagged: {flag}" if flag else "(no flag on file)"),
                      GAP_FINDINGS=(" ; ".join(gaps[:20]) or "none"),
                      BUSINESS_OUTCOME=biz, TRANSCRIPTS=_deal_transcripts(u, calls, cc))
        A.write_json(os.path.join(out, f"{u['unit_index']:03d}.json"),
                     {"unit_index": u["unit_index"], "account": acct,
                      "out_path": f"analysis/technical_win/deal_{u['unit_index']:03d}.json", "prompt": prompt})
        n += 1
    print(f"== emitted {n} technical-win tasks -> {out}")
    print(f"   Each output must include its unit_index and account (echo the task's identity fields).")


def postmortem_tasks(wd, cfg):
    org = cfg.get("org_name")
    calls = {c["call_id"]: c for c in A.read_json(os.path.join(wd, "canonical", "transcripts.json"))}
    cc = A.load_call_company(wd, cfg)
    deals = {d["deal_id"]: d for d in A.read_json(os.path.join(wd, "canonical", "deals.json"))} if os.path.exists(os.path.join(wd, "canonical", "deals.json")) else {}
    hist = A.read_json(os.path.join(wd, "canonical", "stage_history.json")) if os.path.exists(os.path.join(wd, "canonical", "stage_history.json")) else {}
    notes = A.read_json(os.path.join(wd, "canonical", "notes.json")) if os.path.exists(os.path.join(wd, "canonical", "notes.json")) else {}
    tw = {}
    for f in glob.glob(os.path.join(wd, "analysis", "technical_win", "deal_*.json")):
        d = A.read_json(f); tw[d.get("unit_index")] = d
    poc_by = _poc_by_acct(wd, cfg)
    co_by_unit = _callout_by_unit(wd)
    opp = A.read_json(os.path.join(wd, "analysis", "opp_index.json"))
    tmpl = load_template("postmortem.md")
    out = os.path.join(wd, "analysis", "tasks", "postmortem"); os.makedirs(out, exist_ok=True)
    n = 0
    for u in opp:
        if not u.get("in_scope_call_ids"):
            continue
        acct = u.get("account")
        findings = []
        for co in co_by_unit.get(u["unit_index"], []):
            for rp in co.get("reps", []):
                for fp in (rp.get("failure_points") or [])[:2]:
                    findings.append(f"{co.get('date')} {rp.get('rep_name')}: {fp.get('label')} ({(fp.get('why') or '')[:80]})")
        deal_objs = [deals[d] for d in u.get("deal_ids", []) if d in deals]
        se_stage = ", ".join(cc.get(cid, {}).get("se_stage") or "" for cid in u.get("in_scope_call_ids", []) if cc.get(cid, {}).get("se_stage")) or "unknown"
        sh = []
        for d in deal_objs:
            for r in (hist.get(d["deal_id"]) or hist.get(d.get("deal_name")) or []):
                if r.get("modified_time") and r.get("moved_to"):
                    sh.append(f"{r.get('from_stage')}->{r['moved_to']} ({(r.get('modified_time') or '')[:10]})")
        nt = []
        for d in deal_objs:
            for nn in (notes.get(d["deal_id"]) or notes.get(d.get("deal_name")) or []):
                nt.append(f"[{(nn.get('created') or '')[:10]}] {(nn.get('content') or '')[:240]}")
        meddic = {}
        for d in deal_objs:
            for k, v in (d.get("meddic") or {}).items():
                if v and not meddic.get(k):
                    meddic[k] = str(v)[:200]
        twd = tw.get(u["unit_index"]) or {}
        tw_line = f"{twd.get('technical_win_state')}" if twd else "(not inferred)"
        prompt = fill(tmpl, ORG=org, ACCOUNT=acct, SE_STAGE=se_stage,
                      TECH_WIN=tw_line, POC_CRITERIA=_poc_criteria_text(acct, poc_by, cfg),
                      CRM_MEDDIC=(" | ".join(f"{k}: {v}" for k, v in meddic.items()) or "(CRM MEDDIC empty)"),
                      STAGE_HISTORY=(" ; ".join(sh[-12:]) or "none"),
                      NOTES=(" ; ".join(nt[:14]) or "none"),
                      FINDINGS=(" ; ".join(findings[:14]) or "none"),
                      TRANSCRIPTS=_deal_transcripts(u, calls, cc))
        A.write_json(os.path.join(out, f"{u['unit_index']:03d}.json"),
                     {"unit_index": u["unit_index"], "account": acct,
                      "out_path": f"analysis/postmortem/deal_{u['unit_index']:03d}.json", "prompt": prompt})
        n += 1
    print(f"== emitted {n} post-mortem tasks -> {out}")


def adherence_tasks(wd, cfg, sample):
    org = cfg.get("org_name")
    calls = {c["call_id"]: c for c in A.read_json(os.path.join(wd, "canonical", "transcripts.json"))}
    cos = [A.read_json(f) for f in sorted(glob.glob(os.path.join(wd, "analysis", "call_out", "call_*.json")))]
    cos = [c for c in cos if c.get("reps")]
    if sample and len(cos) > sample:
        step = max(1, len(cos) // sample)
        cos = cos[::step][:sample]
    tmpl = load_template("adherence_check.md")
    out = os.path.join(wd, "analysis", "tasks", "adherence"); os.makedirs(out, exist_ok=True)
    for co in cos:
        c = calls.get(co["call_id"])
        if not c:
            continue
        maker = [{"rep_name": r.get("rep_name"), "archetype": r.get("archetype"),
                  "scores": {d: {"score": (v or {}).get("score"), "why": (v or {}).get("why"), "quote": (v or {}).get("quote")}
                             for d, v in (r.get("scores") or {}).items() if isinstance(v, dict)},
                  "demo_lenses": r.get("demo_lenses"),
                  "failure_points": r.get("failure_points") or []} for r in co.get("reps", [])]
        prompt = fill(tmpl, ORG=org, ACCOUNT=co.get("account"), DATE=co.get("date"),
                      MAKER_OUTPUT=json.dumps(maker, ensure_ascii=False, indent=1),
                      TRANSCRIPT=A.transcript_text(c, max_chars=TXT_CAP))
        A.write_json(os.path.join(out, f"{co['call_id']}.json"),
                     {"call_id": co["call_id"], "account": co.get("account"),
                      "out_path": f"analysis/adherence_calls/check_{co['call_id']}.json", "prompt": prompt})
    print(f"== emitted {len(cos)} adherence tasks -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["naming", "doc-ingest", "technical_win", "postmortem", "adherence"])
    ap.add_argument("--workdir", default=os.environ.get("AUDIT_WORKDIR", ""))
    ap.add_argument("--sample", type=int, default=24)
    args = ap.parse_args()
    wd = args.workdir or A.workdir()
    cfg = A.load_config(wd)
    if args.phase == "naming":
        naming_tasks(wd, cfg)
    elif args.phase == "doc-ingest":
        doc_ingest_tasks(wd, cfg)
    elif args.phase == "technical_win":
        technical_win_tasks(wd, cfg)
    elif args.phase == "postmortem":
        postmortem_tasks(wd, cfg)
    else:
        adherence_tasks(wd, cfg, args.sample)


if __name__ == "__main__":
    main()
