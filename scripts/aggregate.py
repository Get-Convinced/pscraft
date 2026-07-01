#!/usr/bin/env python3
"""Assemble the NEW per-call report data. Atom = call_out/call_<id>.json (rep x call). Aggregates up to
rep (cross-call recurring failure + signature + composite), deal (post-mortem + its calls + MEDDIC
reality check), and org (dim averages + stall-archetype clusters). Numbers live only at the aggregate;
the call payload stays qualitative-first. -> analysis/report_data.json
"""
import os, re, sys, glob, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A

_SLOP={"synergy":"fit","synergies":"efficiencies","leverage":"use","leveraging":"using","seamless":"smooth","seamlessly":"smoothly","robust":"strong","delve":"go into","cutting-edge":"advanced","cutting edge":"advanced","best-in-class":"leading","state-of-the-art":"advanced","unlock":"open up","game-changer":"big shift","tapestry":"mix","dive deep":"go into detail","deep dive":"detailed look","dive into":"get into","underscore":"stress","underscores":"stresses","underscored":"stressed","underpin":"support","underpins":"supports","underpinned":"supported"}
_SRE=[(re.compile(r"\b"+re.escape(k)+r"\b",re.I),v) for k,v in _SLOP.items()]
# verbatim fields are EVIDENCE: preserve exactly. titles are source data, also verbatim.
_VERB={"quote","evidence","moment","buyer_quote","rep_quote","crm_value","title"}
# em/en/horizontal-bar dashes are banned in authored prose; convert (en-dash between words -> hyphen so
# date ranges like July-August stay readable; everything else -> comma).
_DASH=[(re.compile(r"(?<=\w)–(?=\w)"),"-"),(re.compile(r"\s*[—–―]\s*"),", ")]
def deslop(o,key=None):
    if isinstance(o,str):
        if key in _VERB: return o
        s=o
        for rx,v in _SRE: s=rx.sub(v,s)
        for rx,v in _DASH: s=rx.sub(v,s)
        return s
    if isinstance(o,dict): return {k:deslop(v,k) for k,v in o.items()}
    if isinstance(o,list): return [deslop(x,key) for x in o]
    return o
def num(x):
    try: return float(str(x).replace(",","") or 0)
    except: return 0.0

def main():
    wd=A.workdir(); cfg=A.load_config(wd)
    skill=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rubric=A.load_rubric(skill,cfg)
    DIMS=[d["id"] for d in rubric["dimensions"]]; DIM_NAMES={d["id"]:d["name"] for d in rubric["dimensions"]}
    DIM_GROUP={d["id"]:d["group"] for d in rubric["dimensions"]}; GROUPS=rubric.get("groups",{})
    archs=rubric["role_archetypes"]; smap=cfg.get("stage_map",{})
    calib=rubric.get("composite",{}); DW=calib.get("low_confidence_downweight",0.7); MIND=calib.get("min_dims_for_composite",4)
    calls={c["call_id"]:c for c in A.read_json(os.path.join(wd,"canonical","transcripts.json"))}
    _dp=os.path.join(wd,"canonical","deals.json"); deals={d["deal_id"]:d for d in (A.read_json(_dp) if os.path.exists(_dp) else [])}
    _np=os.path.join(wd,"canonical","notes.json"); notes=A.read_json(_np) if os.path.exists(_np) else {}
    opp={u["unit_index"]:u for u in A.read_json(os.path.join(wd,"analysis","opp_index.json"))}
    roles=A.read_json(os.path.join(wd,"analysis","roles.json"))
    rollup_old=A.read_json(os.path.join(wd,"analysis","rep_rollup.json")) if os.path.exists(os.path.join(wd,"analysis","rep_rollup.json")) else []
    callout=[A.read_json(f) for f in sorted(glob.glob(os.path.join(wd,"analysis","call_out","call_*.json")))]
    pm={}
    for f in glob.glob(os.path.join(wd,"analysis","postmortem","deal_*.json")):
        d=A.read_json(f); pm[d["unit_index"]]=d
    tw={}   # technical_win/deal_<unit>.json -> the craft-side outcome anchor (separate axis)
    for f in glob.glob(os.path.join(wd,"analysis","technical_win","deal_*.json")):
        d=A.read_json(f); tw[d.get("unit_index")]=d
    # integrity pass on the CRM-vs-call check: you cannot 'claim' or 'contradict' a blank CRM field, and
    # you cannot have 'observed'/'contradicted' a field with no call evidence. Demote such mislabels to
    # 'absent' (excluded from the trust-check) so the Observed/Claimed/Contradicted counts are trustworthy.
    for p in pm.values():
        for m in (p.get("meddic_check") or []):
            st=m.get("status"); cv=(m.get("crm_value") or "").strip(); ev=(m.get("evidence") or "").strip()
            if st in ("claimed","contradicted") and not cv: m["status"]="absent"
            elif st in ("observed","contradicted") and not ev: m["status"]="absent"
    role_by_key={r["key"]:r for r in rollup_old}
    funnel=A.read_json(os.path.join(wd,"analysis","funnel.json")) if os.path.exists(os.path.join(wd,"analysis","funnel.json")) else {}

    def composite(dimcells, arch):
        w=(archs.get(arch,{}) or {}).get("weights",{}); n=d_=lw=0.0; used=0; grp=set()
        for dim,cell in dimcells.items():
            v=cell.get("score")
            if not isinstance(v,(int,float)): continue
            wt0=float(w.get(dim,1.0)); wt=wt0
            if str(cell.get("confidence","")).lower()=="low": wt*=DW
            n+=wt*v; d_+=wt; used+=1; grp.add(DIM_GROUP.get(dim))
        if used<MIND or d_==0 or len([g for g in grp if g])<2: return None
        return round(n/d_,2)

    # ---- per-call payload (qualitative-first) + collectors ----
    calls_out=[]; rep_calls=defaultdict(list); rep_dimvals=defaultdict(lambda:defaultdict(list))
    rep_fails=defaultdict(list); rep_sigs=defaultdict(list); deal_callcomps=defaultdict(list)
    org_dimvals=defaultdict(list); rep_arch={}
    for co in callout:
        cid=co["call_id"]; meta=calls.get(cid,{})
        reps_pay=[]
        for r in co.get("reps",[]):
            if A.excluded_rep(r["rep_name"],cfg): continue
            key=A.norm_name(r["rep_name"]); arch=r.get("archetype") or (role_by_key.get(key,{}) or {}).get("archetype")
            if arch: rep_arch[key]=arch
            cells=r.get("scores",{}) if isinstance(r.get("scores"),dict) else {}
            br=r.get("buyer_reaction")
            if isinstance(br,str): r["buyer_reaction"]={"state":br,"evidence":""}
            elif not isinstance(br,dict): r["buyer_reaction"]={}
            sg=r.get("signature")
            if isinstance(sg,str): r["signature"]={"label":sg,"quote":""}
            elif not isinstance(sg,dict): r["signature"]=None
            r["failure_points"]=[fp for fp in (r.get("failure_points") or []) if isinstance(fp,dict)]
            cmp=composite(cells,arch)
            for dim,cell in cells.items():
                if isinstance(cell.get("score"),(int,float)):
                    rep_dimvals[key][dim].append(cell["score"]); org_dimvals[dim].append(cell["score"])
            for fp in (r.get("failure_points") or []):
                rep_fails[key].append({**fp,"account":co["account"],"slug":co["account"],"call_id":cid,"date":co.get("date"),"recording_url":co.get("recording_url")})
            if r.get("signature") and (r["signature"] or {}).get("quote"):
                rep_sigs[key].append({**r["signature"],"account":co["account"],"call_id":cid,"date":co.get("date"),"recording_url":co.get("recording_url")})
            rep_calls[key].append({"call_id":cid,"account":co["account"],"date":co.get("date"),"title":co.get("title"),
                "unit_index":co.get("unit_index"),"composite":cmp,"buyer":(r.get("buyer_reaction") or {}).get("state"),
                "top_fail":(r.get("failure_points") or [{}])[0].get("label")})
            if cmp is not None and co.get("unit_index") is not None: deal_callcomps[co["unit_index"]].append((key,cmp))
            reps_pay.append({"name":r["rep_name"],"archetype":arch,"kind":r.get("kind"),"composite":cmp,
                "demo_lenses":deslop(r.get("demo_lenses")),"gap_contributions":deslop(r.get("gap_contributions") or []),
                "failure_points":[deslop(x) for x in (r.get("failure_points") or [])],
                "signature":deslop(r.get("signature")),"buyer_reaction":deslop(r.get("buyer_reaction")),
                "scores":{d:(cells.get(d) or {}).get("score") for d in DIMS},
                # full per-dim rationale so every composite is self-evident (scored dims only)
                "score_detail":{d:deslop({"score":c.get("score"),"confidence":c.get("confidence"),"why":c.get("why"),"quote":c.get("quote"),"evidence":c.get("evidence")})
                                for d in DIMS for c in [cells.get(d) or {}] if isinstance(c.get("score"),(int,float))}})
        calls_out.append({"call_id":cid,"slug":cid,"account":co["account"],"date":co.get("date"),"title":co.get("title"),
            "recording_url":co.get("recording_url"),"stage":co.get("stage"),"unit_index":co.get("unit_index"),
            "deal_slug":A.slug(co["account"] or f"deal-{co.get('unit_index')}"),"reps":reps_pay})
    calls_out.sort(key=lambda c:c.get("date") or "")

    # ---- reps: cross-call pattern (recurring failure + signature) + composite ----
    def owned_outcomes():
        # credit a deal's outcome to BOTH the AE (owner) and the SE (se_owner), so the SE's deals show
        # up beside their craft (outcomes stay a separate panel; craft is never docked for them).
        owned=defaultdict(list)
        for d in deals.values():
            for who in (d.get("owner",""), d.get("se_owner","")):
                if who and not A.excluded_rep(who,cfg):
                    owned[A.norm_name(A.canonical_rep_name(who,cfg))].append(d)
        return owned
    owned=owned_outcomes(); stall_raw=set(funnel.get("stall_raw_stages",[]))
    reps_out=[]
    for key, cl in rep_calls.items():
        if A.excluded_rep(key,cfg): continue
        arch=(role_by_key.get(key,{}) or {}).get("archetype") or rep_arch.get(key) or cl[0].get("archetype") or "solution-engineer"
        comps=[c["composite"] for c in cl if c["composite"] is not None]
        craft=round(sum(comps)/len(comps),2) if comps else None
        dim_avgs={d:(round(sum(v)/len(v),2) if v else None) for d,v in rep_dimvals[key].items()}
        # recurring failure = dim with most low (1-2) occurrences, with up to 3 verbatim examples from different calls
        lowcount=Counter()
        for d,v in rep_dimvals[key].items():
            lowcount[d]+=sum(1 for x in v if x<=2)
        rec_dim=max(lowcount,key=lambda d:lowcount[d]) if lowcount and max(lowcount.values())>0 else None
        rec_examples=[f for f in rep_fails[key] if f.get("dim")==rec_dim][:3] if rec_dim else (rep_fails[key][:3])
        hi=Counter()
        for d,v in rep_dimvals[key].items(): hi[d]+=sum(1 for x in v if x>=4)
        sig_dim=max(hi,key=lambda d:hi[d]) if hi and max(hi.values())>0 else None
        sig_ex=next((s for s in rep_sigs[key] if s.get("dim")==sig_dim),None) or (rep_sigs[key][0] if rep_sigs[key] else None)
        bar=(archs.get(arch,{}) or {}).get("bar")
        oc=owned.get(key,[])
        outcomes={"deals_owned":len(oc),"won":sum(1 for d in oc if smap.get(d["stage"])=="won"),
                  "lost":sum(1 for d in oc if smap.get(d["stage"])=="lost"),
                  "stalled":sum(1 for d in oc if d["stage"] in stall_raw),
                  "arr":round(sum(num(d.get("arr")) for d in oc))}
        monthly=defaultdict(list)
        for c in cl:
            if c["composite"] is not None and c.get("date"): monthly[c["date"][:7]].append(c["composite"])
        reps_out.append({"key":key,"slug":A.slug(role_by_key.get(key,{}).get("name") or cl[0]["account"] if False else key),
            "name":(role_by_key.get(key,{}) or {}).get("name") or _name_from_calls(cl,callout,key),
            "archetype":arch,"bar":bar,"craft":craft,"vs_bar":(round(craft-bar,2) if (craft and bar) else None),
            "n_calls":len(cl),"rank_eligible":len(comps)>=cfg.get("min_calls_to_rank_se",cfg.get("min_calls_to_rank_rep",3)),
            "dim_avgs":dim_avgs,
            "recurring":{"dim":rec_dim,"name":DIM_NAMES.get(rec_dim),"n":lowcount.get(rec_dim,0) if rec_dim else 0,"examples":[deslop(x) for x in rec_examples]},
            "signature":{"dim":sig_dim,"name":DIM_NAMES.get(sig_dim),"example":deslop(sig_ex)} if sig_dim else None,
            "outcomes":outcomes,"monthly":{m:round(sum(v)/len(v),2) for m,v in monthly.items()},
            "calls":sorted([{ "call_id":c["call_id"],"slug":c["call_id"],"account":c["account"],"date":c["date"],
                              "composite":c["composite"],"buyer":c["buyer"],"top_fail":c["top_fail"]} for c in cl], key=lambda x:x["date"] or "")})
    # fix slug to name-based
    for r in reps_out: r["slug"]=A.slug(r["name"])
    reps_out.sort(key=lambda r:(not r["rank_eligible"], -(r["craft"] or 0)))

    # ---- deals: post-mortem + its calls + composite ----
    deals_out=[]
    deal_calls=defaultdict(list)
    for c in calls_out:
        if c.get("unit_index") is not None: deal_calls[c["unit_index"]].append(c)
    for ui,u in opp.items():
        cs=deal_calls.get(ui,[])
        if not cs and ui not in pm: continue
        comps=[x[1] for x in deal_callcomps.get(ui,[])]
        acct=u.get("account")
        deals_out.append({"unit_index":ui,"slug":A.slug(acct or f"deal-{ui}"),"account":acct,
            "outcome":u.get("outcome"),"arr":u.get("arr"),"composite":(round(sum(comps)/len(comps),2) if comps else None),
            "postmortem":deslop(pm.get(ui)),"technical_win":deslop(tw.get(ui)),"n_calls":len(cs),
            "calls":[{"call_id":c["call_id"],"date":c["date"],"title":c["title"],"recording_url":c["recording_url"],
                      "reps":[{"name":rp["name"],"composite":rp["composite"]} for rp in c["reps"]]} for c in cs]})
    deals_out.sort(key=lambda d:({"stalled":0,"open":1,"won":2,"lost":3}.get(d["outcome"],4),-num(d["arr"])))

    # ---- org: dim avgs, stall archetypes, motion ----
    org_dim_avgs={d:(round(sum(v)/len(v),2) if v else None) for d,v in org_dimvals.items()}
    dv=sorted([(d,org_dim_avgs[d]) for d in DIMS if org_dim_avgs.get(d) is not None],key=lambda x:x[1])
    arche=Counter(p.get("stall_archetype") for p in pm.values() if p.get("stall_archetype"))
    arche_examples=defaultdict(list)
    for p in pm.values():
        a=p.get("stall_archetype")
        if a: arche_examples[a].append({"account":p.get("account"),"slug":A.slug(p.get("account") or ''),"why":p.get("why_hold"),"arr":p.get("arr")})
    # MEDDIC reality: across postmortems, how often each field is observed vs merely claimed
    med=defaultdict(lambda:Counter())
    for p in pm.values():
        for m in (p.get("meddic_check") or []):
            med[m.get("field")][m.get("status")]+=1
    org={"org_name":cfg.get("org_name"),"as_of":cfg.get("as_of_date"),"stall_label":cfg.get("terminology",{}).get("stall_label"),
        "n_calls_scored":len(calls_out),"n_deals":len(deals_out),"n_reps":len(reps_out),
        "n_reps_ranked":sum(1 for r in reps_out if r["rank_eligible"]),
        "dim_avgs":org_dim_avgs,"floor_dims":[{"dim":d,"name":DIM_NAMES[d],"avg":v} for d,v in dv[:4]],
        "strong_dims":[{"dim":d,"name":DIM_NAMES[d],"avg":v} for d,v in dv[-3:][::-1]],
        "stall_archetypes":[{"key":k,"n":n,"examples":sorted(arche_examples[k],key=lambda x:-num(x.get('arr')))[:4]} for k,n in arche.most_common()],
        "meddic_reality":{f:dict(c) for f,c in med.items()},"funnel":funnel.get("funnel"),"caveats":cfg.get("caveats",[]),
        # currency is whatever the run discovered (config.currency), never hard-coded
        "currency":cfg.get("currency") or {"symbol":"$","style":"short"}}
    adh_path=os.path.join(wd,"analysis","adherence.json")
    if os.path.exists(adh_path): org["adherence"]=A.read_json(adh_path)
    cnc_path=os.path.join(wd,"analysis","council_output.json")
    if os.path.exists(cnc_path): org["council"]=deslop(A.read_json(cnc_path))
    dg_path=os.path.join(wd,"analysis","diagnosis.json")
    if os.path.exists(dg_path): org["diagnosis"]=deslop(A.read_json(dg_path))
    # ---- technical win (the craft-side OUTCOME anchor), reported SEPARATELY from craft + business outcome ----
    tw_states=Counter(t.get("technical_win_state") for t in tw.values() if t.get("technical_win_state"))
    tw_reached=sum(tw_states.get(s,0) for s in ("won_written","won_verbal"))
    tw_denom=sum(n for s,n in tw_states.items() if s!="na")
    biz_won=sum(1 for d in deals_out if d.get("outcome")=="won")
    biz_denom=sum(1 for d in deals_out if d.get("outcome") in ("won","lost","stalled"))
    org["technical_win"]={"states":dict(tw_states),"reached":tw_reached,"n_deals_with_tw":len(tw),
        "tw_rate":(round(tw_reached/tw_denom,3) if tw_denom else None),
        "business_win_rate":(round(biz_won/biz_denom,3) if biz_denom else None)}
    # ---- quarters (QoQ trend), only surfaced when the corpus spans >= reporting.min_quarters ----
    def _q(dt):
        try: y,m=int(dt[:4]),int(dt[5:7]); return f"{y}-Q{(m-1)//3+1}"
        except: return None
    qv=defaultdict(list)
    for co in calls_out:
        for rp in co.get("reps",[]):
            if isinstance(rp.get("composite"),(int,float)) and co.get("date"):
                qq=_q(co["date"])
                if qq: qv[qq].append(rp["composite"])
    quarters=[{"quarter":k,"avg_craft":round(sum(v)/len(v),2),"n":len(v)} for k,v in sorted(qv.items())]
    min_q=(cfg.get("reporting",{}) or {}).get("min_quarters",2)
    org["quarters"]=quarters if len(quarters)>=min_q else []
    # ---- demo lens rollup ----
    org["demo"]={"n_demos_scored":sum(1 for co in calls_out for rp in co.get("reps",[]) if rp.get("demo_lenses"))}
    out={"org":org,"calls":calls_out,"deals":deals_out,"reps":reps_out,"dims":DIMS,"dim_names":DIM_NAMES,"dim_groups":DIM_GROUP,"groups":GROUPS}
    out=deslop(out)
    A.write_json(os.path.join(wd,"analysis","report_data.json"),out)
    print(f"== report_data_v2: {len(calls_out)} calls, {len(deals_out)} deals, {len(reps_out)} reps, {len(pm)} post-mortems")
    print(f"   floor dims: {[(d['dim'],d['avg']) for d in org['floor_dims']]}")
    print(f"   stall archetypes: {dict(arche)}")

def _name_from_calls(cl, callout, key):
    for co in callout:
        for r in co.get("reps",[]):
            if A.norm_name(r["rep_name"])==key: return r["rep_name"]
    return key

if __name__=="__main__":
    main()
