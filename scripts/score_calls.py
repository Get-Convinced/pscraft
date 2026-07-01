#!/usr/bin/env python3
"""Per-call scoring driver (PSCraft). Deterministic task-prep (which calls, which technical explainers,
their responsible dims, the SE stage, the deal arc, the POC criteria, the competitor) is shared; only the
model call differs by engine.

  python3 scripts/score_calls.py --workdir <dir> --emit-tasks   # HOST-AGENT mode: write filled prompts to
                                                                 # analysis/tasks/score/, no model call.
                                                                 # The host runs one subagent per task and
                                                                 # writes each result to analysis/call_out/.
  python3 scripts/score_calls.py --workdir <dir>                 # API mode: fill + call engine/llm.py + write
                                                                 # analysis/call_out/ directly. Resume-safe.

PSCraft scores the TECHNICAL EXPLAINER(S) on each call: whoever carried the technical explaining (from
call_company.json technical_explainers). A seller who did the technical explaining is scored as
seller-doing-technical. One task per in-scope call (the read-every-call invariant). Reads
prompts/call_score.md so the prompt has ONE source of truth.
"""
import os, re, sys, glob, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)        # scripts/  -> lib
sys.path.insert(0, SKILL)       # skill root -> engine
from lib import audit as A
from lib import scoring

PER_CALL_CAP = 22000


def load_template(name):
    t = open(os.path.join(SKILL, "prompts", name), encoding="utf-8").read()
    return re.sub(r"^<!--.*?-->\s*", "", t, flags=re.S)  # drop the usage comment header


def fill(t, **kw):
    for k, v in kw.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def build_anchors(rubric):
    """The rubric block the scorer reads: per-dim 1-5 anchors + the stage_expectations matrix (the NA
    logic) rendered as a compact table. Pure string plumbing over the rubric."""
    anchors = scoring.rubric_anchors(rubric)
    se = rubric.get("stage_expectations") or {}
    stages = se.get("stages") or []
    matrix = se.get("matrix") or {}
    if not stages or not matrix:
        return anchors
    lines = ["", "STAGE EXPECTATIONS (what is DUE vs NA at this call's SE stage; a move not yet due is NA, not a failure):",
             "  stage order: " + " -> ".join(stages)]
    for dim, row in matrix.items():
        cells = ", ".join(f"{s}:{row.get(s, '-')}" for s in stages)
        lines.append(f"  {dim}: {cells}")
    legend = se.get("legend") or {}
    if legend:
        lines.append("  legend: " + "; ".join(f"{k}={v}" for k, v in legend.items()))
    return anchors + "\n" + "\n".join(lines)


def demo_calibration_text(rubric):
    dc = rubric.get("demo_calibration") or {}
    if not dc:
        return "(no demo calibration provided)"
    out = [dc.get("so_what_test", "")]
    for k, v in (dc.get("lenses") or {}).items():
        out.append(f"- {k}: {v}")
    return "\n".join(x for x in out if x)


def poc_criteria_for(account, poc_by_acct, cfg):
    plans = poc_by_acct.get(A.norm_account(account or "", cfg), [])
    lines = []
    for p in plans:
        for c in (p.get("criteria") or []):
            t = (c.get("text") or "").strip()
            if not t:
                continue
            mt = " ".join(x for x in [c.get("metric"), c.get("target")] if x)
            lines.append(f"- {t}" + (f" [{mt}]" if mt.strip() else ""))
    return "\n".join(lines[:20]) or "(no POC criteria doc)"


def build_call_ctx(cid, unit, cc, calls, deals, roles, rubric, cfg, poc_by_acct):
    """Assemble the scoring context for ONE call. The scored people are the TECHNICAL EXPLAINERS on this
    call (call_company.json technical_explainers). Each is scored on the SE rubric; a person whose
    per-person archetype is not a dedicated SE but who explained here is scored as seller-doing-technical."""
    archs = rubric["role_archetypes"]
    info = cc.get(cid, {}); c = calls.get(cid)
    if not c:
        return None
    # who to score: the technical explainers on THIS call; fall back to org_participants if the namer
    # did not tag explainers (older records), still filtered to scoreable archetypes.
    explainers = info.get("technical_explainers") or []
    candidates = explainers or (info.get("org_participants") or [])
    rep_set = {}
    for nm0 in dict.fromkeys(candidates):     # preserve order, dedupe
        if A.excluded_rep(nm0, cfg):
            continue
        r = roles.get(A.norm_name(nm0)) or {}
        arch = r.get("archetype")
        if arch == "partner-external" or not (r.get("is_org_rep", True)):
            continue
        # a person tagged as a technical explainer on this call is scored, even if their standing
        # archetype is ae-nontechnical: score them as a seller wearing the SE hat.
        if arch in (None, "ae-nontechnical") and nm0 in explainers:
            arch = "seller-doing-technical"
        a = archs.get(arch, {})
        if not a or a.get("excluded_from_scoring"):
            continue
        cn = A.canonical_rep_name(r.get("name", nm0), cfg); k = A.norm_name(cn)
        rep_set[k] = {"key": k, "name": cn, "archetype": arch, "kind": a.get("kind"),
                      "label": a.get("label"), "responsible_dims": a.get("responsible_dims", []),
                      "responsibility": a.get("responsible_for", "")}
    if not rep_set:
        return None
    deal_objs = [deals[d] for d in (unit.get("deal_ids") or []) if d in deals]
    se_stage = info.get("se_stage") or None
    competitor = next((d.get("competitor") for d in deal_objs if d.get("competitor")), None)
    arc = []
    for pc in unit.get("in_scope_call_ids", []):
        if pc == cid:
            continue
        pcc = calls.get(pc); pi = cc.get(pc, {})
        if pcc and (pcc.get("date") or "") < (c.get("date") or ""):
            arc.append({"date": pcc.get("date"), "one_line": (pi.get("one_line") or pcc.get("title") or "")[:160]})
    arc.sort(key=lambda x: x["date"] or "")
    return {"call_id": cid, "account": unit.get("account"), "unit_index": unit["unit_index"],
            "date": c.get("date"), "title": c.get("title"), "recording_url": c.get("recording_url"),
            "se_stage": se_stage, "competitor": competitor,
            "poc_criteria": poc_criteria_for(unit.get("account"), poc_by_acct, cfg),
            "arc": arc, "reps": list(rep_set.values()),
            "transcripts": A.transcript_text(c, max_chars=PER_CALL_CAP)}


def render_prompt(ctx, tmpl, org, oneliner, kb, anchors, democal):
    reps = "\n".join(f"  - {r['name']} [{r['key']}] = {r['archetype']} ({r['label']}); RESPONSIBLE DIMS: "
                     f"{', '.join(r['responsible_dims'])}. {r['responsibility']}" for r in ctx["reps"])
    arc = "\n".join(f"  - {a['date']}: {a['one_line']}" for a in ctx["arc"]) or "  (this is the first recorded call on the deal)"
    return fill(tmpl, ORG=org, ONELINER=oneliner, COMPANY_CONTEXT=kb[:6500], ACCOUNT=ctx["account"],
                SE_STAGE=ctx["se_stage"] or "unknown", ARC=arc, REPS=reps,
                RUBRIC_ANCHORS=anchors, DEMO_CALIBRATION=democal,
                POC_CRITERIA=ctx["poc_criteria"], COMPETITOR=ctx["competitor"] or "(none named)",
                TRANSCRIPT=ctx["transcripts"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.environ.get("AUDIT_WORKDIR", ""))
    ap.add_argument("--emit-tasks", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    wd = args.workdir or A.workdir()
    cfg = A.load_config(wd)
    rubric = A.load_rubric(SKILL, cfg)
    anchors = build_anchors(rubric)
    democal = demo_calibration_text(rubric)
    tmpl = load_template("call_score.md")
    kbp = os.path.join(wd, "company_context.md")
    kb = open(kbp, encoding="utf-8").read()[:7000] if os.path.exists(kbp) else ""
    org = cfg.get("org_name"); oneliner = cfg.get("product_oneliner", "")
    calls = {c["call_id"]: c for c in A.read_json(os.path.join(wd, "canonical", "transcripts.json"))}
    deals = {d["deal_id"]: d for d in A.read_json(os.path.join(wd, "canonical", "deals.json"))} if os.path.exists(os.path.join(wd, "canonical", "deals.json")) else {}
    poc_by_acct = {}
    pocp = os.path.join(wd, "canonical", "poc_plans.json")
    if os.path.exists(pocp):
        for p in A.read_json(pocp):
            poc_by_acct.setdefault(A.norm_account(p.get("account") or "", cfg), []).append(p)
    cc = A.load_call_company(wd, cfg)
    roles = A.read_json(os.path.join(wd, "analysis", "roles.json"))
    opp = A.read_json(os.path.join(wd, "analysis", "opp_index.json"))
    call2unit = {}
    for u in opp:
        for cid in u.get("in_scope_call_ids", []):
            call2unit[cid] = u
    targets = [cid for cid in call2unit if cc.get(cid, {}).get("call_phase") not in ("postsale", "internal")]

    outdir = os.path.join(wd, "analysis", "call_out"); os.makedirs(outdir, exist_ok=True)
    taskdir = os.path.join(wd, "analysis", "tasks", "score"); os.makedirs(taskdir, exist_ok=True)
    if not args.force:
        done = {os.path.basename(f)[5:-5] for f in glob.glob(outdir + "/call_*.json")}
        targets = [cid for cid in targets if cid not in done]
    if args.limit:
        targets = targets[:args.limit]

    if args.emit_tasks:
        n = 0
        for cid in targets:
            ctx = build_call_ctx(cid, call2unit[cid], cc, calls, deals, roles, rubric, cfg, poc_by_acct)
            if not ctx:
                continue
            A.write_json(os.path.join(taskdir, f"{cid}.json"), {
                "call_id": cid, "account": ctx["account"], "unit_index": ctx["unit_index"],
                "se_stage": ctx["se_stage"],
                "out_path": f"analysis/call_out/call_{cid}.json",
                "reps": [{"key": r["key"], "name": r["name"], "archetype": r["archetype"], "kind": r["kind"]} for r in ctx["reps"]],
                "prompt": render_prompt(ctx, tmpl, org, oneliner, kb, anchors, democal)})
            n += 1
        print(f"== emitted {n} scoring tasks -> {taskdir}")
        print(f"   HOST-AGENT: run one subagent per task file; have it return the JSON from prompts/call_score.md")
        print(f"   and write it to the task's out_path. Then run merge_scores.py + aggregate.py.")
        return

    # API mode
    from engine import llm
    print(f"== score_calls (API {llm.PROVIDER}/{llm.MODEL_REASONER}): {len(targets)} calls, workers={args.workers}")

    def run(cid):
        ctx = build_call_ctx(cid, call2unit[cid], cc, calls, deals, roles, rubric, cfg, poc_by_acct)
        if not ctx:
            return {"call_id": cid, "_skip": "no scoreable technical explainers"}
        r = llm.chat_json([{"role": "user", "content": render_prompt(ctx, tmpl, org, oneliner, kb, anchors, democal)}],
                          model=llm.MODEL_REASONER, max_tokens=15000, temperature=0.0)
        auth = {x["key"]: x for x in ctx["reps"]}
        reps = []
        for rep in (r.get("reps") or []):
            nr = scoring.normalize_rep(rep)
            k = A.norm_name(A.canonical_rep_name(nr.get("rep_name", ""), cfg))
            a = auth.get(k) or auth.get(A.norm_name(nr.get("rep_key", "")))
            if not a:
                continue
            nr.update({"rep_key": a["key"], "rep_name": a["name"], "archetype": a["archetype"], "kind": a.get("kind")})
            for f in ("failure_points", "signature", "buyer_reaction", "demo_lenses", "gap_contributions"):
                nr[f] = rep.get(f)
            reps.append(nr)
        return {"call_id": cid, "unit_index": ctx["unit_index"], "account": ctx["account"], "date": ctx["date"],
                "title": ctx["title"], "recording_url": ctx["recording_url"], "se_stage": ctx["se_stage"], "reps": reps}

    def on_done(i, res):
        if res and not res.get("_skip") and not res.get("_error"):
            A.write_json(os.path.join(outdir, f"call_{res['call_id']}.json"), res)
    results = llm.map_concurrent(targets, run, workers=args.workers, label="score", on_done=on_done)
    ok = sum(1 for r in results if r and not r.get("_skip") and not r.get("_error"))
    print(f"== scored {ok}/{len(targets)} calls -> {outdir}")


if __name__ == "__main__":
    main()
