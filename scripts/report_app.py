#!/usr/bin/env python3
"""Render ONE self-contained interactive HTML app from analysis/report_data.json.

Hash-routed SPA, all data embedded. Views: Org diagnosis (floor moves, stall-archetype clusters, MEDDIC
reality, org radar, stark examples), Reps (searchable/sortable leaderboard), Rep detail (radar vs org +
recurring failure with cross-call verbatim + per-deal deep-dive of where they break), Deals (filterable
ledger), Deal detail (post-mortem: how it failed + the one change they should have made + MEDDIC reality
check), Call detail (qualitative-first: buyer line -> rep line -> why; numbers demoted to a footer grid).
Global search + filters + cross-links. No build step, no network. -> <workdir>/report.html
"""
import os, sys, json, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A

CSS = r"""
*{box-sizing:border-box}
:root{--ink:#1f1d1b;--bg:#fff;--mut:#6f6a64;--line:#ececec;--red:#d7043a;--teal:#0f766e;--amber:#a86a00;
--c5a:#e3f3e9;--c5b:#1c7c40;--c4a:#eaf3e0;--c4b:#4f8f2f;--c3a:#fbf3d6;--c3b:#9a7a00;--c2a:#fde6d8;--c2b:#bd5b1e;--c1a:#fbe0dd;--c1b:#b3261e}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:var(--ink);background:var(--bg);line-height:1.5;font-size:15px}
a{color:inherit;text-decoration:none}a.lnk{color:var(--red);font-weight:700}a.lnk:hover{text-decoration:underline}
.shell{max-width:1120px;margin:0 auto;padding:0 22px}
.top{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.top .shell{display:flex;gap:14px;align-items:center;min-height:60px}
.brand{font-weight:800;letter-spacing:-.3px;white-space:nowrap}.nav{display:flex;gap:6px;margin-left:6px;flex-wrap:wrap}
.nav a{font-size:13.5px;border:1px solid var(--line);padding:7px 13px;border-radius:999px;color:#444;white-space:nowrap}
.nav a.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.searchwrap{margin-left:auto;position:relative}
#q{width:280px;max-width:42vw;padding:9px 13px;border:1px solid #ddd;border-radius:999px;font-size:14px;outline:none}
#q:focus{border-color:var(--ink)}
#results{position:absolute;top:46px;right:0;width:420px;max-width:88vw;background:#fff;border:1px solid #ddd;border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.16);max-height:60vh;overflow:auto;display:none}
#results a{display:block;padding:10px 14px;border-bottom:1px solid #f3f3f3;font-size:13.5px}
#results a:hover,#results a.act{background:#faf7f2}#results .k{font-size:10.5px;text-transform:uppercase;color:#999;font-weight:800;margin-right:7px}
.hero{padding:44px 0 22px}.eyebrow{display:inline-block;padding:6px 12px;border:1px solid var(--line);border-radius:999px;color:var(--mut);font-size:12.5px;margin-bottom:14px}
h1{font-size:clamp(27px,3.6vw,44px);line-height:1.05;margin:0;font-weight:600;letter-spacing:-.5px;max-width:940px}
.hero p{font-size:17.5px;color:#3f3f3f;max-width:860px}
.section{padding:26px 0;border-top:1px solid var(--line)}
.kicker{color:var(--red);font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:.07em}
h2{font-size:23px;font-weight:600;margin:6px 0 4px;letter-spacing:-.3px}h3{font-size:17px;margin:0;font-weight:600}
.lead{color:#3f3f3f;max-width:820px;margin:6px 0}.muted{color:var(--mut)}.small{font-size:13px}.tag{font-size:12px;color:var(--mut)}
.card{background:#fff;border:1px solid #e3e3e3;border-radius:14px;padding:16px 18px;margin-top:12px}
.grid{display:grid;gap:12px}.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}
@media(max-width:760px){.g2,.g3{grid-template-columns:1fr}#q{width:150px}.nav a{padding:6px 9px}}
table{border-collapse:collapse;width:100%;font-size:13.5px}td,th{text-align:left;padding:8px 9px;border-bottom:1px solid #f1f1f1;vertical-align:top}
th{color:#999;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;cursor:pointer;user-select:none}th:hover{color:var(--ink)}
tr.rowlink:hover{background:#faf7f2;cursor:pointer}
.sc{display:inline-block;min-width:24px;text-align:center;border-radius:6px;font-weight:800;font-size:12px;padding:3px 6px}
.q{margin:7px 0;padding:9px 13px;border-left:3px solid var(--c1b);background:#fafafa;border-radius:0 8px 8px 0;font-size:13.5px}
.q.rep{border-left-color:var(--teal)}.q cite{display:block;color:#999;font-style:normal;font-size:11px;margin-top:4px}
.pill{display:inline-block;padding:3px 11px;border-radius:999px;font-size:12px;font-weight:800}
.pill.won{background:#e9fbf7;color:var(--teal)}.pill.lost{background:#f1f1f1;color:#555}.pill.stalled,.pill.hold{background:#fff1f4;color:var(--c1b)}.pill.open,.pill.active{background:#eef5ff;color:#2f5f98}
.fail{border:1px solid #eee;border-left:4px solid var(--red);border-radius:12px;padding:14px 16px;margin-top:10px}
.good{border:1px solid #eee;border-left:4px solid var(--teal);border-radius:12px;padding:14px 16px;margin-top:10px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.chip{font-size:12.5px;border:1px solid #ddd;padding:6px 12px;border-radius:999px;cursor:pointer;color:#555;background:#fff}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.bar{height:8px;border-radius:6px;background:#f0eeea;overflow:hidden}.bar>span{display:block;height:100%}
.kpi{display:flex;gap:18px;flex-wrap:wrap}.kpi .b{flex:1;min-width:120px}.kpi .n{font-size:28px;font-weight:700;letter-spacing:-.5px}
footer{padding:28px 0;color:#999;font-size:12.5px;border-top:1px solid var(--line);margin-top:18px}
.crumb{font-size:13px;color:var(--mut);margin:18px 0 0}.crumb a{color:var(--red);font-weight:600}
.radarwrap{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.lgd{font-size:12px;color:var(--mut)}.lgd b{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
details>summary{cursor:pointer;color:#999;font-size:13px;list-style:none}details>summary::-webkit-details-marker{display:none}
"""

JS = r"""
const D = JSON.parse(document.getElementById('DATA').textContent);
const DIMS=D.dims, DN=D.dim_names, DG=D.dim_groups, GROUPS=D.groups||{};
const GKEYS=Object.keys(GROUPS);
const callsById={}, dealsBySlug={}, repsBySlug={};
D.calls.forEach(c=>callsById[c.call_id]=c);
D.deals.forEach(d=>dealsBySlug[d.slug]=d);
D.reps.forEach(r=>repsBySlug[r.slug]=r);
const GLABEL={discovery:'Technical discovery',demo:'Demo craft',validation:'POC / validation',rigor:'Technical rigor',objection_competition:'Objection & competitive',enablement:'Champion & status-quo'};

const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const num=v=>(typeof v==='number'&&isFinite(v));
// currency is data-driven (org.currency = {symbol, style}); never hard-coded. style 'indian' uses
// lakh/crore, anything else uses thousand/million/billion. Symbol comes from what the run discovered.
function money(n){n=parseFloat(n)||0;const C=(typeof D!=='undefined'&&D.org&&D.org.currency)||{symbol:'$',style:'short'};const s=C.symbol||'';
  if(C.style==='indian')return n>=1e7?s+(n/1e7).toFixed(2)+' Cr':n>=1e5?s+(n/1e5).toFixed(1)+' L':s+Math.round(n).toLocaleString('en-IN');
  if(n>=1e9)return s+(n/1e9).toFixed(2).replace(/\.?0+$/,'')+'B';
  if(n>=1e6)return s+(n/1e6).toFixed(2).replace(/\.?0+$/,'')+'M';
  if(n>=1e3)return s+(n/1e3).toFixed(1).replace(/\.0$/,'')+'K';
  return s+Math.round(n).toLocaleString('en-US');}
function scColor(v){const r=Math.round(v);const m={5:['var(--c5a)','var(--c5b)'],4:['var(--c4a)','var(--c4b)'],3:['var(--c3a)','var(--c3b)'],2:['var(--c2a)','var(--c2b)'],1:['var(--c1a)','var(--c1b)']}[r];return m||['#f3f3f3','#999'];}
function sc(v){if(!num(v))return '<span class="sc" style="background:#f3f3f3;color:#bbb">NA</span>';const[a,b]=scColor(v);return `<span class="sc" style="background:${a};color:${b}">${(+v.toFixed(2)).toString().replace(/\.00$/,'')}</span>`;}
function pill(k){k=(k||'').toLowerCase();return `<span class="pill ${esc(k)}">${esc(k||'-')}</span>`;}
function q(speaker,txt,rec){if(!txt)return'';const rep=/^(rep|seller)/i.test(speaker||'');const cite=[esc(speaker),rec?`<a class=lnk href="${esc(rec)}" target=_blank>recording</a>`:''].filter(Boolean).join(' ');return `<div class="q ${rep?'rep':''}">${esc(txt)}${cite?`<cite>${cite}</cite>`:''}</div>`;}
const ARCH={"feature-tour-no-discovery":"Feature tour with no technical discovery","criteria-less-poc":"POC run with no exit criteria","poc-scope-creep":"POC drifted, scope crept","security-blocker-unresolved":"A security or integration blocker went unresolved","champion-not-enabled":"Technical champion left unable to sell internally","lost-to-competitor-technical":"Lost the technical evaluation to a competitor","value-not-quantified":"Value never tied to the buyer's technical success criteria","technical-win-no-deal":"Technical win reached, deal lost elsewhere","structurally-dead-disqualify":"Structurally dead, parked instead of disqualified","economic_buyer_budget_not_secured":"Economic buyer or budget not secured","scope_expanding_no_exit_criteria":"Scope kept expanding with no exit criteria","criteria_less_poc":"POC ran with no exit criteria","no_committed_next_step":"No committed next step","won":"Won","still-active":"Still active"};
function archLabel(k){return ARCH[k]||String(k||'').replace(/[_-]+/g,' ').replace(/(^|\s)\w/g,c=>c.toUpperCase());}

// group average from a per-dim map
function groupAvgs(dimMap){const out={};GKEYS.forEach(g=>{const vs=DIMS.filter(d=>DG[d]===g).map(d=>dimMap[d]).filter(num);out[g]=vs.length?vs.reduce((a,b)=>a+b,0)/vs.length:null;});return out;}
// per-rep evidence the model flagged: failure points (drag) and signatures (lift), each carrying its dim
function repMoments(repName){const fp=[],hi=[];D.calls.forEach(c=>(c.reps||[]).forEach(rp=>{if(rp.name!==repName)return;
  (rp.failure_points||[]).forEach(f=>{if(f.dim)fp.push({dim:f.dim,label:f.label,quote:f.rep_quote,why:f.why,account:c.account,date:c.date,call_id:c.call_id});});
  const sg=rp.signature;if(sg&&sg.dim&&sg.quote)hi.push({dim:sg.dim,label:sg.label,quote:sg.quote,why:sg.why,account:c.account,date:c.date,call_id:c.call_id});}));return {fp,hi};}
// the full per-dimension scoring behind a composite, sorted worst-first, each with its rationale + the
// rep's own quote. This is what makes a craft number self-evident rather than a bare figure.
function scoreBreakdown(rp,rec,openByDefault,tag){
  const det=rp.score_detail||{};
  const ds=DIMS.filter(d=>det[d]&&num(det[d].score)).sort((a,b)=>det[a].score-det[b].score);
  if(!ds.length)return '';
  const rows=ds.map(d=>{const x=det[d];return `<tr><td style="width:30px;vertical-align:top">${sc(x.score)}</td><td><b>${esc(DN[d]||d)}</b>`
    +`${(x.confidence&&x.confidence!=='high')?` <span class="tag">${esc(x.confidence)} confidence</span>`:''}`
    +`<div class="small" style="color:#3f3f3f">${esc(x.why||'')}</div>`
    +`${x.evidence?`<div class="q rep" style="white-space:pre-wrap;margin-top:6px">${esc(x.evidence)}${rec?`<cite><a class=lnk href="${esc(rec)}" target=_blank>recording</a></cite>`:''}</div>`:(x.quote?q('Rep',x.quote,rec):'')}</td></tr>`;}).join('');
  return `<details style="margin-top:10px"${openByDefault?' open':''}><summary>How the ${num(rp.composite)?'<b>'+rp.composite+'</b>':''} craft score was built${tag?' ('+esc(tag)+')':''}, all ${ds.length} dimensions in play, worst first</summary>`
    +`<div class="card" style="margin-top:8px"><table>${rows}</table></div>`
    +`<p class="small muted" style="margin-top:6px">The composite is the role-weighted mean of these dimensions. A move not yet due at this call's stage is scored NA and left out.</p></details>`;
}

function radar(seriesList, size=300){ // seriesList:[{name,color,vals:{group:val}}]
  const cx=size/2, cy=size/2, R=size*0.36, n=GKEYS.length, max=5;
  const pt=(i,r)=>{const ang=-Math.PI/2 + i*2*Math.PI/n;return [cx+r*Math.cos(ang), cy+r*Math.sin(ang)];};
  let g='';
  for(let ring=1;ring<=5;ring++){const r=R*ring/5;let p=GKEYS.map((_,i)=>pt(i,r).join(',')).join(' ');g+=`<polygon points="${p}" fill="none" stroke="#eee" stroke-width="1"/>`;}
  GKEYS.forEach((k,i)=>{const[x,y]=pt(i,R);g+=`<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#eee"/>`;
    const[lx,ly]=pt(i,R+16);const anchor=lx<cx-4?'end':lx>cx+4?'start':'middle';
    g+=`<text x="${lx}" y="${ly}" font-size="10.5" fill="#777" text-anchor="${anchor}" dominant-baseline="middle">${esc(GLABEL[k]||k)}</text>`;});
  seriesList.forEach(s=>{const pts=GKEYS.map((k,i)=>{const v=s.vals[k];return pt(i, v==null?0:R*v/max);});
    g+=`<polygon points="${pts.map(p=>p.join(',')).join(' ')}" fill="${s.color}22" stroke="${s.color}" stroke-width="2"/>`;
    pts.forEach((p,i)=>{if(s.vals[GKEYS[i]]!=null)g+=`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="${s.color}"/>`;});});
  return `<svg viewBox="-84 -6 ${size+168} ${size+12}" width="${size+90}" height="${size}" style="max-width:100%">${g}</svg>`;
}

// failure points for a given rep across calls (returns [{call,account,date,fp}])
function repFails(repName){const out=[];D.calls.forEach(c=>{(c.reps||[]).forEach(rp=>{if(rp.name===repName)(rp.failure_points||[]).forEach(fp=>out.push({call:c,fp}));});});return out;}

/* ---------- CRM trust check shared logic ---------- */
const MCRM={
  MFL:{metric:'Metric',economic_buyer:'Economic buyer',decision_process:'Decision process',decision_criteria:'Decision criteria',champion:'Champion',pain:'Pain',competition:'Competition',paper:'Paper process',technical_win:'Technical win (flag vs call)'},
  TIT:{contradicted:'Contradicted by the call',claimed:'Recorded in the CRM, never earned on a call',observed:'Observed being gathered on a call'},
  idx(){const m={};D.deals.forEach(dl=>{((dl.postmortem||{}).meddic_check||[]).forEach(x=>{const f=x.field;if(!f)return;(m[f]=m[f]||{observed:[],claimed:[],contradicted:[]});if(m[f][x.status])m[f][x.status].push({account:dl.account,slug:dl.slug,crm_value:x.crm_value,evidence:x.evidence});});});return m;},
  card(e,kind){const col=kind==='contradicted'?'var(--c1b)':kind==='claimed'?'var(--c2b)':'var(--c5b)';
    const lab=kind==='contradicted'?'On the call (contradicts the CRM)':kind==='observed'?'On the call':'Never seen being gathered on a call';
    return `<div class="card" style="border-left:4px solid ${col};margin-top:8px"><b><a class=lnk href="#deal/${esc(e.slug)}">${esc(e.account)}</a></b>`
      +`<div class="small" style="margin-top:5px"><span class="tag">RECORDED IN CRM</span> ${esc(e.crm_value||'(blank field)')}</div>`
      +(e.evidence?`<div class="small" style="margin-top:5px;color:${col}"><span class="tag" style="color:${col}">${esc(lab.toUpperCase())}</span> ${esc(e.evidence)}</div>`:`<div class="small muted" style="margin-top:5px">${esc(lab)}.</div>`)+`</div>`;},
  render(det,midx,field,status){
    const fields=field?[field]:Object.keys(midx);
    const order=status?[status]:['contradicted','claimed'];
    let body='';
    order.forEach(st=>{let items=[];fields.forEach(f=>((midx[f]||{})[st]||[]).forEach(e=>items.push(e)));
      if(!items.length)return;
      body+=`<h3 style="margin-top:18px">${this.TIT[st]} <span class="tag">(${items.length})</span></h3>`;
      const cards=items.map(e=>this.card(e,st)).join('');
      body+=(st!=='contradicted'&&items.length>10)?`<details><summary>show ${items.length}</summary>${cards}</details>`:cards;});
    const hint=field?`Field: <b>${this.MFL[field]||field}</b>. `:'';
    const sub=status?`Showing ${status}.`:'Showing the actionable rows (contradicted, then claim-only). Click a green Observed number for the ones the rep earned.';
    det.innerHTML=`<div style="margin-top:6px"><div class="small muted">${hint}${sub}</div>${body||'<p class="small muted" style="margin-top:10px">Nothing in this bucket.</p>'}</div>`;
    document.querySelectorAll('#mchips .chip').forEach(c=>c.classList.toggle('on',(c.dataset.f||'')===(field||'')));}
};
function viewCrm(field){
  const o=D.org, mr=o.meddic_reality||{};
  if(!Object.keys(mr).length)return `<div class="section">No CRM check data.</div>`;
  field=field&&MCRM.MFL[field]?field:null;
  let to=0,tc=0,tx=0;Object.values(mr).forEach(c=>{to+=c.observed||0;tc+=c.claimed||0;tx+=c.contradicted||0;});
  let h=`<div class="crumb"><a href="#org">Diagnosis</a> / CRM trust check</div>
   <div class="hero"><div class="eyebrow">CRM trust check</div><h1>What the CRM records, what the calls actually show.</h1>
   <p>For every qualification detail we checked whether a rep was seen earning it on a recorded call. A field sitting in the CRM that was never gathered on a call is a claim, not a fact. Across the book: <b style="color:var(--c5b)">${to}</b> observed, <b style="color:var(--c2b)">${tc}</b> recorded-only, <b style="color:var(--c1b)">${tx}</b> contradicted by a call.</p></div>
   <div class="section"><div class="card" style="overflow-x:auto"><table><tr><th>Field</th><th>Observed on a call</th><th>CRM claim only</th><th>Contradicted</th></tr>`;
  Object.entries(mr).forEach(([f,c])=>h+=`<tr><td><b>${esc(MCRM.MFL[f]||f)}</b></td>
    <td class="mcell" data-f="${esc(f)}" data-s="observed" style="color:var(--c5b);font-weight:700;cursor:pointer">${c.observed||0}</td>
    <td class="mcell" data-f="${esc(f)}" data-s="claimed" style="color:var(--c2b);font-weight:700;cursor:pointer">${c.claimed||0}</td>
    <td class="mcell" data-f="${esc(f)}" data-s="contradicted" style="color:var(--c1b);font-weight:700;cursor:pointer">${c.contradicted||0}</td></tr>`);
  h+=`</table></div><p class="small muted" style="margin-top:6px">Click any number to see the deals behind it; click a field chip to filter. 'RECORDED IN CRM' is the CRM field value; the colored line is the verbatim call evidence.</p>
    <div class="chips" id="mchips"><span class="chip${field?'':' on'}" data-f="">All fields</span>${Object.keys(mr).map(f=>`<span class="chip${f===field?' on':''}" data-f="${esc(f)}">${esc(MCRM.MFL[f]||f)}</span>`).join('')}</div>
    <div id="mdetail"></div></div>`;
  setTimeout(()=>{const det=document.getElementById('mdetail');if(!det)return;const midx=MCRM.idx();
    document.querySelectorAll('.mcell').forEach(c=>c.onclick=()=>MCRM.render(det,midx,c.dataset.f,c.dataset.s));
    document.querySelectorAll('#mchips .chip').forEach(c=>c.onclick=()=>MCRM.render(det,midx,c.dataset.f||null,null));
    MCRM.render(det,midx,field,null);},0);
  return h;
}

/* ---------- COUNCIL ---------- */
function viewCouncil(){
  const o=D.org, c=o.council;
  if(!c)return `<div class="crumb"><a href="#org">Diagnosis</a> / Council</div><div class="section"><h2>No council output yet.</h2><p class="muted">Run digest.py then council_run.py, then re-aggregate.</p></div>`;
  const syn=c.synthesis||{}, SEV={high:'var(--c1b)',medium:'var(--c2b)',low:'#888'};
  let h=`<div class="crumb"><a href="#org">Diagnosis</a> / Council</div>
   <div class="hero"><div class="eyebrow">Consultant council</div><h1>Four independent reviewers, read blind, then reconciled.</h1>
   <p>Each seat reviewed the whole book through one lens, blind to the others. The synthesis reconciles them into the highest-leverage changes. This is the judgment layer sitting on top of the per-call scoring.</p></div>`;
  if((syn.ranked_changes||[]).length){
    h+=`<div class="section"><div class="kicker">The synthesis</div><h2>Highest-leverage changes, in order.</h2>`;
    syn.ranked_changes.forEach((rc,i)=>h+=`<div class="card"><h3>${i+1}. ${esc(rc.change)}</h3><div class="small" style="color:#3f3f3f;margin-top:5px"><b>Why:</b> ${esc(rc.rationale)}</div>${rc.expected_effect?`<div class="small muted" style="margin-top:3px"><b>Expected effect:</b> ${esc(rc.expected_effect)}</div>`:''}</div>`);
    h+=`</div>`;
  }
  if((syn.consensus||[]).length||(syn.tensions||[]).length){
    h+=`<div class="section"><div class="grid g2">`;
    if((syn.consensus||[]).length)h+=`<div class="card"><div class="kicker">Consensus</div><ul class="small" style="color:#3f3f3f;line-height:1.7;margin:6px 0 0;padding-left:18px">${syn.consensus.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`;
    if((syn.tensions||[]).length)h+=`<div class="card"><div class="kicker">Tensions</div><ul class="small" style="color:#3f3f3f;line-height:1.7;margin:6px 0 0;padding-left:18px">${syn.tensions.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`;
    h+=`</div></div>`;
  }
  if(syn.craft_vs_outcome_note)h+=`<div class="section"><div class="kicker">Craft versus outcome</div><p class="lead">${esc(syn.craft_vs_outcome_note)}</p></div>`;
  h+=`<div class="section"><div class="kicker">The four seats</div><h2>Each lens, on the record.</h2>`;
  (c.seats||[]).forEach(s=>{
    h+=`<div class="card"><h3>${esc(s.seat)}</h3>`;
    [['Why deals stall technically',s.answer_why_deals_stall_technically||s.answer_why_deals_stall],['What SEs miss',s.answer_what_ses_miss||s.answer_what_reps_miss],['Demo quality',s.answer_demo_quality||s.answer_who_solutions],['The one change',s.answer_one_change]].filter(a=>a[1]).forEach(a=>h+=`<div class="small" style="margin-top:5px"><b>${a[0]}:</b> ${esc(a[1])}</div>`);
    (s.findings||[]).forEach(f=>h+=`<div style="margin-top:8px;padding-left:10px;border-left:3px solid ${SEV[f.severity]||'#ccc'}"><div class="small"><b style="color:${SEV[f.severity]||'#888'}">${esc((f.severity||'').toUpperCase())}</b> ${esc(f.claim)}</div><div class="small muted">${esc(f.evidence)}</div></div>`);
    h+=`</div>`;
  });
  h+=`</div>`;
  return h;
}

/* ---------- ORG ---------- */
function viewOrg(){
  const o=D.org;
  const floor=o.floor_dims.map(f=>`${f.name} (${f.avg})`).join(', ');
  const dg=o.diagnosis||{};
  let h=`<div class="hero"><div class="eyebrow">${esc(o.org_name)} · per-call audit · ${esc(o.as_of)}</div>
    <h1>${dg.headline?esc(dg.headline):'Every call read on its own. The same few moves missed on nearly all of them.'}</h1>
    <p>${dg.floor_summary?esc(dg.floor_summary):(o.n_calls_scored+' calls scored across '+o.n_reps+' engineers and '+o.n_deals+' deals. The floor repeats everywhere: '+esc(floor)+'.')}</p>
    <p class="small muted">${o.n_calls_scored} calls scored one by one; craft is scored apart from outcome. Open any call to see the transcript, the exchange, and why.</p></div>`;
  if((dg.fixes||[]).length){
    h+=`<div class="section"><div class="kicker">What to fix</div><h2>The moves to change, worst first.</h2><div class="grid g2">`;
    dg.fixes.forEach((f,i)=>h+=`<div class="card"><h3>${i+1}. ${esc(f.move)}</h3><div class="small" style="color:#3f3f3f;margin-top:6px"><b>On the calls:</b> ${esc(f.what_happens)}</div><div class="small" style="margin-top:7px;padding:8px 11px;background:#eef7f3;border-radius:8px"><b>Do this next call:</b> ${esc(f.do_this)}</div></div>`);
    h+=`</div></div>`;
  }
  // org radar + KPIs
  const ga=groupAvgs(o.dim_avgs);
  h+=`<div class="section"><div class="kicker">The shape of the gap</div><h2>Where the team is strong and where it is bare.</h2>
    <div class="radarwrap"><div>${radar([{name:'Team',color:'#d7043a',vals:ga}])}</div>
    <div class="kpi"><div class="b"><div class="n">${o.n_calls_scored}</div><div class="tag">calls scored</div></div>
    <div class="b"><div class="n">${o.n_reps}</div><div class="tag">reps</div></div>
    <div class="b"><div class="n">${o.n_deals}</div><div class="tag">deals</div></div></div></div></div>`;
  // stall archetypes
  if((o.stall_archetypes||[]).length){
    h+=`<div class="section"><div class="kicker">Why deals die</div><h2>The same handful of stalls, again and again.</h2><div class="grid g2">`;
    o.stall_archetypes.forEach(a=>{const ex=(a.examples||[]).map(x=>`<a class=lnk href="#deal/${esc(x.slug)}">${esc(x.account)}</a>`).join(', ');
      h+=`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px"><h3>${esc(archLabel(a.key))}</h3><span class="tag">${a.n} deals</span></div><p class="small muted" style="margin:6px 0 0">e.g. ${ex}</p></div>`;});
    h+=`</div><p class="small" style="margin-top:10px"><a class=lnk href="#deals">All deal post-mortems &rarr;</a></p></div>`;
  }
  // stark examples: worst failure points on floor dims
  const floorSet=new Set(o.floor_dims.map(f=>f.dim));
  let stark=[];
  D.calls.forEach(c=>(c.reps||[]).forEach(rp=>(rp.failure_points||[]).forEach(fp=>{if(floorSet.has(fp.dim)&&fp.rep_quote&&fp.buyer_quote)stark.push({c,rp,fp});})));
  stark=stark.slice(0,8);
  if(stark.length){
    h+=`<div class="section"><div class="kicker">Stark examples</div><h2>What it looks like on the call.</h2>`;
    stark.forEach(s=>{h+=`<div class="fail"><div style="display:flex;justify-content:space-between;gap:8px"><div class="kicker">${esc(DN[s.fp.dim]||s.fp.dim)}</div><a class=lnk href="#call/${esc(s.c.call_id)}">${esc(s.rp.name)} · ${esc(s.c.account)} &rarr;</a></div>
      <div style="font-weight:600;margin:3px 0 6px">${esc(s.fp.label)}</div>${q('Buyer',s.fp.buyer_quote,s.c.recording_url)}${q('Rep',s.fp.rep_quote,s.c.recording_url)}<div class="small" style="color:#3f3f3f;margin-top:5px"><b>Why:</b> ${esc(s.fp.why)}</div></div>`;});
    h+=`</div>`;
  }
  // MEDDIC reality (summary only; full drill-down lives on the CRM check page)
  const mr=o.meddic_reality||{};
  if(Object.keys(mr).length){
    h+=`<div class="section"><div class="kicker">CRM trust check</div><h2>How often the qualification was actually earned on a call.</h2>
      <div class="card" style="overflow-x:auto"><table><tr><th>Field</th><th>Observed on a call</th><th>CRM claim only</th><th>Contradicted</th></tr>`;
    Object.entries(mr).forEach(([f,c])=>h+=`<tr class="rowlink" onclick="location.hash='#crm/${esc(f)}'"><td><b>${esc(MCRM.MFL[f]||f)}</b></td>
      <td style="color:var(--c5b);font-weight:700">${c.observed||0}</td>
      <td style="color:var(--c2b);font-weight:700">${c.claimed||0}</td>
      <td style="color:var(--c1b);font-weight:700">${c.contradicted||0}</td></tr>`);
    h+=`</table></div><p class="small muted" style="margin-top:6px">A CRM field never seen being gathered on a call is treated as a claim, not a fact.</p>
      <p class="small" style="margin-top:4px"><a class=lnk href="#crm">Open the full CRM trust breakdown, recorded versus observed versus contradicted, deal by deal &rarr;</a></p></div>`;
  }
  // maker-checker adherence
  const ad=o.adherence;
  if(ad){const v=ad.verdicts||{};const tot=ad.reps_audited||1;
    h+=`<div class="section"><div class="kicker">Method check (maker-checker)</div><h2>An independent model audited the scoring.</h2>
    <p class="lead">${ad.calls_audited} calls re-read by ${esc(ad.checker_model)} (the checker) against the ${esc(ad.maker_model)} scorer (the maker), audited on six calibration rules. Pass rate <b>${Math.round((ad.pass_rate||0)*100)}%</b> of ${ad.reps_audited} rep audits; mean score gap on disputed dimensions ${ad.mean_abs_rescore_delta==null?'not available':ad.mean_abs_rescore_delta}.</p>
    <div class="grid g3"><div class="card"><div class="n" style="font-size:26px;font-weight:700;color:var(--c5b)">${v.pass||0}</div><div class="tag">pass</div></div>
    <div class="card"><div class="n" style="font-size:26px;font-weight:700;color:var(--c2b)">${v.minor||0}</div><div class="tag">minor flags</div></div>
    <div class="card"><div class="n" style="font-size:26px;font-weight:700;color:var(--c1b)">${v.major||0}</div><div class="tag">major (review)</div></div></div>`;
    if(Object.keys(ad.violations_by_rule||{}).length){h+=`<div class="card"><b class="small">Violations by rule</b><div style="margin-top:6px">`+Object.entries(ad.violations_by_rule).map(([r,n])=>`<span style="display:inline-block;margin:3px 10px 3px 0"><span class="tag">${esc(r)} ${esc((ad.rules||{})[r]||'')}</span> <b>${n}</b></span>`).join('')+`</div></div>`;}
    if((ad.majors||[]).length){h+=`<details style="margin-top:10px"><summary>${ad.majors.length} calls flagged for human review</summary><div class="card" style="margin-top:8px">`+ad.majors.map(m=>`<div style="padding:6px 0;border-bottom:1px solid #f1f1f1;font-size:13px"><a class=lnk href="#call/${esc(m.call_id)}">${esc(m.account)} · ${esc(m.rep)}</a> <span class="muted">${esc(m.reason)}</span></div>`).join('')+`</div></details>`;}
    h+=`</div>`;}
  // full dim list
  h+=`<div class="section"><div class="kicker">Every move, org-wide</div><div class="card">`;
  GKEYS.forEach(g=>{const dims=DIMS.filter(d=>DG[d]===g&&o.dim_avgs[d]!=null);if(!dims.length)return;
    h+=`<div style="font-size:11px;text-transform:uppercase;color:var(--red);font-weight:800;margin:12px 0 6px">${esc(GLABEL[g]||g)}</div>`;
    dims.forEach(d=>{const v=o.dim_avgs[d];const[,col]=scColor(v);h+=`<div style="display:flex;align-items:center;gap:10px;padding:3px 0;font-size:13.5px"><span style="flex:1">${esc(DN[d])}</span><div class="bar" style="width:120px"><span style="width:${v/5*100}%;background:${col}"></span></div><b style="color:${col};width:34px;text-align:right">${v}</b></div>`;});});
  h+=`</div></div>`;
  if((o.caveats||[]).length)h+=`<div class="section"><div class="kicker">How to read this</div><div class="card"><ul class="small" style="color:#3f3f3f;line-height:1.7;margin:0;padding-left:18px">${o.caveats.map(c=>`<li>${esc(c)}</li>`).join('')}</ul></div></div>`;
  return h;
}

/* ---------- REPS list ---------- */
let repSort={k:'craft',dir:1};
function viewReps(){
  let h=`<div class="hero"><div class="eyebrow">Reps</div><h1>What each rep repeatedly does well, and badly.</h1><p>Aggregated across every call. Craft is not docked for a lost deal. Click a rep for the radar, the recurring failure in their own words, and a deal-by-deal breakdown.</p></div>
  <div class="section"><div class="chips" id="repchips"><span class="chip on" data-f="ranked">Ranked (3+ calls)</span><span class="chip" data-f="all">All</span></div><div id="reptbl"></div></div>`;
  setTimeout(()=>{bindRepTable();},0);
  return h;
}
function bindRepTable(){
  const chips=document.getElementById('repchips');let mode='ranked';
  function draw(){
    let rows=D.reps.filter(r=>mode==='all'||r.rank_eligible);
    const key=repSort.k;
    rows.sort((a,b)=>{let x,y;if(key==='craft'||key==='n_calls'){x=a[key]||0;y=b[key]||0;}else if(key==='name'){x=a.name;y=b.name;}else if(key==='won'){x=a.outcomes.won;y=b.outcomes.won;}return (x<y?-1:x>y?1:0)*repSort.dir;});
    let t=`<div class="card" style="overflow-x:auto"><table><tr>
      <th data-k="name">Rep</th><th>Role</th><th data-k="craft">Craft</th><th data-k="n_calls">Calls</th><th>Recurring failure</th><th>Signature</th><th data-k="won">Outcomes</th></tr>`;
    rows.forEach(r=>{const o=r.outcomes;t+=`<tr class="rowlink" data-go="#rep/${esc(r.slug)}">
      <td><b>${esc(r.name)}</b></td><td class="small">${esc(r.archetype)}</td><td>${sc(r.craft)}</td><td>${r.n_calls}</td>
      <td class="small" style="color:var(--c1b)">${esc((r.recurring||{}).name||'')}</td>
      <td class="small" style="color:var(--teal)">${esc((r.signature||{}).name||'')}</td>
      <td class="small muted">${o.won} won · ${o.lost} lost · ${o.stalled} held</td></tr>`;});
    t+=`</table></div>`;
    document.getElementById('reptbl').innerHTML=t;
    document.querySelectorAll('#reptbl th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;repSort.dir=(repSort.k===k)?-repSort.dir:(k==='name'?1:-1);repSort.k=k;draw();});
    document.querySelectorAll('#reptbl tr[data-go]').forEach(tr=>tr.onclick=()=>location.hash=tr.dataset.go);
  }
  chips.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{chips.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));ch.classList.add('on');mode=ch.dataset.f;draw();});
  draw();
}

/* ---------- REP detail ---------- */
function viewRep(slug){
  const r=repsBySlug[slug];if(!r)return `<div class="section">Rep not found.</div>`;
  let h=`<div class="crumb"><a href="#reps">Reps</a> / ${esc(r.name)}</div>
   <div class="hero"><div class="eyebrow">Rep · ${esc(r.archetype)}</div><h1>${esc(r.name)}</h1>
   <p>Across ${r.n_calls} scored calls. Craft composite <b>${num(r.craft)?r.craft:'NA'}</b> versus the role bar ${r.bar}. Outcomes are shown apart; craft is not marked down for a lost deal.</p></div>`;
  // radar vs org + per-axis explainers (why the rep sits where they do on each spoke)
  const ga=groupAvgs(r.dim_avgs), oa=groupAvgs(D.org.dim_avgs);
  const mom=repMoments(r.name);
  h+=`<div class="section"><div class="kicker">Profile</div><h2>Where this rep is strong and bare, against the team.</h2>
    <div class="radarwrap"><div>${radar([{name:'Team',color:'#bbb',vals:oa},{name:r.name,color:'#d7043a',vals:ga}])}</div>
    <div><div class="lgd"><b style="background:#d7043a"></b>${esc(r.name)}</div><div class="lgd"><b style="background:#bbb"></b>Team average</div>
    <p class="small muted" style="max-width:330px;margin-top:8px">Each spoke is the mean of this rep's per-call scores on that area's dimensions (1-5). A move not yet due at a call's stage is scored NA and left out, so a spoke only reflects moments where the move was actually in play. The cards below show why each spoke sits where it does.</p></div></div>`;
  h+=`<div class="section"><div class="kicker">Why the rep sits where they do, spoke by spoke</div><div class="grid g2">`;
  GKEYS.forEach(g=>{
    const dims=DIMS.filter(d=>DG[d]===g&&num(r.dim_avgs[d]));
    if(!dims.length){h+=`<div class="card"><h3>${esc(GLABEL[g]||g)} <span class="tag">not scored</span></h3><div class="small muted" style="margin-top:6px">No moves in this area came up at a scorable point on this rep's calls.</div></div>`;return;}
    const rv=ga[g], tv=oa[g];
    const delta=(num(rv)&&num(tv))?(rv>=tv?`<span style="color:var(--c5b)">at/above team ${tv.toFixed(1)}</span>`:`<span style="color:var(--c1b)">below team ${tv.toFixed(1)}</span>`):'';
    const ds=dims.slice().sort((a,b)=>r.dim_avgs[a]-r.dim_avgs[b]);  // worst dim first, shows the drag
    const bars=ds.map(d=>{const v=r.dim_avgs[d];const cc=scColor(v)[1];return `<div style="display:flex;align-items:center;gap:8px;padding:2px 0;font-size:12.5px"><span style="flex:1">${esc(DN[d])}</span><div class="bar" style="width:84px"><span style="width:${v/5*100}%;background:${cc}"></span></div><b style="color:${cc};width:28px;text-align:right">${v}</b></div>`;}).join('');
    const worst=mom.fp.filter(x=>DG[x.dim]===g)[0];
    const best=mom.hi.filter(x=>DG[x.dim]===g)[0];
    h+=`<div class="card"><div style="display:flex;justify-content:space-between;align-items:baseline"><h3>${esc(GLABEL[g]||g)} ${sc(rv)}</h3><span class="tag">${delta}</span></div>
      <div style="margin-top:8px">${bars}</div>
      <div class="small muted" style="margin-top:6px">Spoke = mean of the ${ds.length} dimension${ds.length>1?'s':''} above, worst first.</div>`;
    if(worst)h+=`<div style="margin-top:8px;padding-left:10px;border-left:3px solid #f0d0d0"><div class="small"><b style="color:var(--c1b)">Drags it down, ${esc(DN[worst.dim])}</b> · <a class=lnk href="#call/${esc(worst.call_id)}">${esc(worst.account)} ${esc(worst.date)}</a></div>${worst.quote?`<div class="small muted" style="font-style:italic">"${esc(worst.quote)}"</div>`:''}<div class="small" style="color:#3f3f3f">${esc(worst.why)}</div></div>`;
    if(best)h+=`<div style="margin-top:8px;padding-left:10px;border-left:3px solid #bfe3d2"><div class="small"><b style="color:var(--teal)">Lifts it, ${esc(DN[best.dim])}</b> · <a class=lnk href="#call/${esc(best.call_id)}">${esc(best.account)} ${esc(best.date)}</a></div>${best.quote?`<div class="small muted" style="font-style:italic">"${esc(best.quote)}"</div>`:''}</div>`;
    if(!worst&&!best)h+=`<div class="small muted" style="margin-top:8px">No single moment flagged here; the spoke reflects the dimension averages above.</div>`;
    h+=`</div>`;
  });
  h+=`</div></div>`;
  // recurring failure with cross-call verbatim
  const rec=r.recurring||{};
  if(rec.dim){
    h+=`<div class="section"><div class="kicker">The recurring failure</div><h2>${esc(rec.name)}, on ${rec.n} calls.</h2><p class="lead">The move this rep most often fumbles, in their own words across different calls.</p>`;
    (rec.examples||[]).forEach(ex=>{h+=`<div class="fail"><div class="small muted">${esc(ex.account)} · ${esc(ex.date)}</div><div style="font-weight:600;margin:3px 0">${esc(ex.label)}</div>${ex.rep_quote?q('Rep',ex.rep_quote,ex.recording_url):''}<div class="small" style="color:#3f3f3f"><b>Why:</b> ${esc(ex.why)}</div></div>`;});
    h+=`</div>`;
  }
  // signature
  const sg=r.signature;
  if(sg&&(sg.example||{}).quote){const ex=sg.example;h+=`<div class="section"><div class="kicker" style="color:var(--teal)">Signature strength</div><h2>${esc(sg.name)}.</h2><div class="good"><div class="small muted">${esc(ex.account)} · ${esc(ex.date)}</div>${q('Rep',ex.quote,ex.recording_url)}<div class="small" style="color:#3f3f3f">${esc(ex.why)}</div></div></div>`;}
  // deal-by-deal deep dive: group rep.calls by account, attach worst fails from embedded calls
  const byDeal={};
  (r.calls||[]).forEach(c=>{(byDeal[c.account]=byDeal[c.account]||{account:c.account,slug:null,calls:[],comp:[]});byDeal[c.account].calls.push(c);if(num(c.composite))byDeal[c.account].comp.push(c.composite);
    const cc=callsById[c.call_id];if(cc)byDeal[c.account].slug=cc.deal_slug;});
  const deals=Object.values(byDeal).sort((a,b)=>(a.comp.length?a.comp.reduce((x,y)=>x+y,0)/a.comp.length:9)-(b.comp.length?b.comp.reduce((x,y)=>x+y,0)/b.comp.length:9));
  h+=`<div class="section"><div class="kicker">Where it breaks, deal by deal</div><h2>The same rep, deal by deal.</h2>`;
  deals.forEach(dl=>{const avg=dl.comp.length?dl.comp.reduce((a,b)=>a+b,0)/dl.comp.length:null;
    const fails=[];dl.calls.forEach(c=>{const cc=callsById[c.call_id];if(cc)(cc.reps||[]).forEach(rp=>{if(rp.name===r.name)(rp.failure_points||[]).forEach(fp=>fails.push({fp,call:cc}));});});
    h+=`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline"><h3>${dl.slug?`<a class=lnk href="#deal/${esc(dl.slug)}">${esc(dl.account)}</a>`:esc(dl.account)}</h3><span class="tag">${dl.calls.length} call${dl.calls.length>1?'s':''} · craft ${num(avg)?sc(avg):'NA'}</span></div>`;
    fails.slice(0,3).forEach(f=>{h+=`<div style="margin-top:8px;padding-left:10px;border-left:3px solid #f0d0d0"><div class="small"><b>${esc(DN[f.fp.dim]||f.fp.dim)}:</b> ${esc(f.fp.label)} <a class=lnk href="#call/${esc(f.call.call_id)}">call &rarr;</a></div>${f.fp.rep_quote?`<div class="small muted" style="font-style:italic">"${esc(f.fp.rep_quote)}"</div>`:''}</div>`;});
    if(!fails.length)h+=`<div class="small muted" style="margin-top:6px">No failure points flagged on this deal.</div>`;
    // the full per-call scoring behind the craft number, so it is self-evident, not just the top fails
    dl.calls.forEach(c=>{const cc=callsById[c.call_id];if(!cc)return;const rp=(cc.reps||[]).find(x=>x.name===r.name);if(rp)h+=scoreBreakdown(rp,cc.recording_url,false,`${cc.date}`);});
    h+=`</div>`;});
  h+=`</div>`;
  // outcomes + call table
  const o=r.outcomes;
  h+=`<div class="section"><div class="kicker">Outcomes, separate from craft</div><p class="lead">${o.deals_owned} owned · <span style="color:var(--teal)">${o.won} won</span> · ${o.lost} lost · <span style="color:var(--c1b)">${o.stalled} held</span> · ${money(o.arr)}</p></div>`;
  h+=`<div class="section"><div class="kicker">Call by call</div><div class="card" style="overflow-x:auto"><table><tr><th>Date</th><th>Account</th><th>Craft</th><th>Buyer</th></tr>`;
  (r.calls||[]).slice().sort((a,b)=>(a.date<b.date?1:-1)).forEach(c=>h+=`<tr class="rowlink" data-go="#call/${esc(c.call_id)}"><td>${esc(c.date)}</td><td><b>${esc(c.account)}</b></td><td>${num(c.composite)?sc(c.composite):'-'}</td><td class="small">${esc(c.buyer||'-')}</td></tr>`);
  h+=`</table></div></div>`;
  setTimeout(()=>document.querySelectorAll('tr[data-go]').forEach(tr=>tr.onclick=()=>location.hash=tr.dataset.go),0);
  return h;
}

/* ---------- DEALS list ---------- */
function viewDeals(){
  let h=`<div class="hero"><div class="eyebrow">Deals</div><h1>Why deals go to ${esc(D.org.stall_label)}, and the pattern behind it.</h1><p>Every deal carries a post-mortem: how it failed and the one change that would have mattered. Filter by outcome, or search up top.</p></div>
   <div class="section"><div class="chips" id="dchips"><span class="chip on" data-f="all">All</span><span class="chip" data-f="won">Won</span><span class="chip" data-f="lost">Lost</span><span class="chip" data-f="stalled">Stalled/Hold</span></div><div id="dtbl"></div></div>`;
  setTimeout(()=>{const chips=document.getElementById('dchips');let f='all';
    function draw(){let rows=D.deals.filter(d=>f==='all'||(d.outcome||'').toLowerCase().includes(f==='stalled'?'hold':f)||(f==='stalled'&&/stall/i.test(d.outcome||'')));
      let t=`<div class="card" style="overflow-x:auto"><table><tr><th>Deal</th><th>Outcome</th><th>Value</th><th>Calls</th><th>Why it is where it is</th></tr>`;
      rows.forEach(d=>{const pm=d.postmortem||{};t+=`<tr class="rowlink" data-go="#deal/${esc(d.slug)}"><td><b>${esc(d.account)}</b></td><td>${pill(d.outcome)}</td><td class="small">${money(d.arr)}</td><td>${d.n_calls}</td><td class="small muted">${esc((pm.why_hold||pm.headline||'').slice(0,150))}</td></tr>`;});
      t+=`</table></div>`;document.getElementById('dtbl').innerHTML=t;
      document.querySelectorAll('#dtbl tr[data-go]').forEach(tr=>tr.onclick=()=>location.hash=tr.dataset.go);}
    chips.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{chips.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));ch.classList.add('on');f=ch.dataset.f;draw();});draw();},0);
  return h;
}

/* ---------- DEAL detail ---------- */
function viewDeal(slug){
  const d=dealsBySlug[slug];if(!d)return `<div class="section">Deal not found.</div>`;
  const pm=d.postmortem||{};
  let h=`<div class="crumb"><a href="#deals">Deals</a> / ${esc(d.account)}</div>
   <div class="hero"><div class="eyebrow">Deal post-mortem · ${pill(d.outcome)} · ${money(d.arr)}</div><h1>${esc(d.account)}</h1><p>${esc(pm.headline||'')}</p></div>`;
  if(pm.arc)h+=`<div class="section"><div class="kicker">Arc</div><p class="lead">${esc(pm.arc)}</p></div>`;
  const lp=pm.lost_conviction||{};
  if(lp&&lp.moment)h+=`<div class="section"><div class="kicker">Where technical conviction was lost</div><h2>${esc(lp.date||'')}</h2>${q('',lp.moment)}<p class="small" style="color:#3f3f3f"><b>Why:</b> ${esc(lp.why)}</p></div>`;
  if(pm.why_hold){h+=`<div class="section"><div class="kicker">How it failed</div><p class="lead">${esc(pm.why_hold)}</p>`;
    if(pm.stall_archetype)h+=`<p class="small"><b>Pattern:</b> ${esc(archLabel(pm.stall_archetype))} · ${pm.coachable?'coachable':'structural'}</p>`;
    if(pm.one_change)h+=`<div class="good" style="border-left-color:var(--red)"><b>What they should have done:</b> ${esc(pm.one_change)}</div>`;
    h+=`</div>`;}
  const pa=pm.poc_arc||{};
  if(pa&&pa.criteria_defined!==undefined)h+=`<div class="section"><div class="kicker">POC arc</div><p class="small">Exit criteria defined: <b>${pa.criteria_defined?'yes':'no'}</b>${pa.criteria_met?' · met: '+esc(String(pa.criteria_met)):''}${pa.criteria_failed?' · failed: '+esc(String(pa.criteria_failed)):''} · written exit: <b>${pa.exit_written?'yes':'no'}</b></p></div>`;
  const tw=d.technical_win;
  if(tw){const TWL={won_written:'Won (written)',won_verbal:'Won (verbal)',in_validation:'In validation',lost_technical:'Lost technical',not_reached:'Not reached',na:'N/A'};
    const GST={addressed_written:['closed, in writing','var(--c5b)'],addressed_verbal:['closed, verbally','var(--c4b)'],acknowledged_open:['open','var(--c3b)'],ignored:['ignored','var(--c1b)']};
    h+=`<div class="section"><div class="kicker">Technical Win</div><h2>Was the solution won on the merits?</h2><p class="lead">State: <b>${esc(TWL[tw.technical_win_state]||tw.technical_win_state||'-')}</b>. <a class=lnk href="#techwin">See all gap ledgers &rarr;</a></p>`;
    const gl=tw.gap_ledger||[];
    if(gl.length){h+=`<div class="card" style="overflow-x:auto"><table><tr><th>Concern the buyer raised</th><th>Status</th><th>Evidence</th></tr>`;
      gl.forEach(g=>{const st=GST[g.status]||[g.status,'#888'];h+=`<tr><td>${esc(g.gap)}${g.raised_by?' <span class="tag">'+esc(g.raised_by)+'</span>':''}</td><td><b style="color:${st[1]}">${esc(st[0])}</b></td><td class="small muted">${esc((g.evidence&&g.evidence.quote)||'')}</td></tr>`;});
      h+=`</table></div>`;}
    h+=`</div>`;}
  const mc=pm.meddic_check||[];
  if(mc.length){const badge={observed:'var(--c5b)',claimed:'var(--c2b)',contradicted:'var(--c1b)',absent:'#999'};
    h+=`<div class="section"><div class="kicker">CRM versus call: was the qualification actually earned?</div><h2>The CRM fields, checked against the calls.</h2><div class="card" style="overflow-x:auto"><table><tr><th>Field</th><th>CRM says</th><th>On the calls</th><th>Evidence</th></tr>`;
    mc.forEach(m=>{const st=m.status||'absent';h+=`<tr><td>${esc(m.field)}</td><td class="small">${esc(m.crm_value||'-')}</td><td><b style="color:${badge[st]||'#999'}">${esc(st)}</b></td><td class="small muted">${esc((m.evidence||'').slice(0,170))}</td></tr>`;});
    h+=`</table></div><p class="small muted" style="margin-top:6px">'claimed' = in the CRM but never seen being gathered on a call, so treat as unverified.</p></div>`;}
  if((d.calls||[]).length){h+=`<div class="section"><div class="kicker">The calls</div><h2>Read any call.</h2><div class="card">`;
    d.calls.forEach(c=>{const reps=(c.reps||[]).map(rp=>`${esc(rp.name)} ${num(rp.composite)?sc(rp.composite):''}`).join(' · ');
      h+=`<div style="padding:8px 0;border-bottom:1px solid #f1f1f1"><a class=lnk href="#call/${esc(c.call_id)}">${esc(c.date)} · ${esc((c.title||'').slice(0,70))}</a>${c.recording_url?' · <a class=lnk href="'+esc(c.recording_url)+'" target=_blank>recording</a>':''} <span class="tag">${reps}</span></div>`;});
    h+=`</div></div>`;}
  return h;
}

/* ---------- CALL detail (qualitative-first) ---------- */
function viewCall(id){
  const c=callsById[id];if(!c)return `<div class="section">Call not found.</div>`;
  const dl=dealsBySlug[c.deal_slug];
  let h=`<div class="crumb">${dl?`<a href="#deal/${esc(dl.slug)}">${esc(c.account)}</a>`:esc(c.account)} / call</div>
   <div class="hero"><div class="eyebrow">Call · ${esc(c.date)}${c.stage?' · '+esc(c.stage):''}</div><h1>${esc(c.account)}</h1>
   <p class="muted">${esc(c.title||'')}${c.recording_url?` · <a class=lnk href="${esc(c.recording_url)}" target=_blank>recording</a>`:''}</p></div>`;
  (c.reps||[]).forEach(rp=>{
    h+=`<div class="section"><div style="display:flex;justify-content:space-between;align-items:baseline"><h2><a class=lnk href="#rep/${esc(slugify(rp.name))}">${esc(rp.name)}</a> <span class="tag">${esc(rp.archetype)}</span></h2><span class="tag">buyer: ${esc((rp.buyer_reaction||{}).state||'-')}</span></div>`;
    const fps=rp.failure_points||[];
    if(fps.length)fps.forEach(fp=>{h+=`<div class="fail"><div class="kicker">${esc(DN[fp.dim]||fp.dim)}</div><div style="font-weight:600;margin:3px 0 6px">${esc(fp.label)}</div>${fp.buyer_quote?q('Buyer',fp.buyer_quote,c.recording_url):''}${fp.rep_quote?q('Rep',fp.rep_quote,c.recording_url):''}<div class="small" style="color:#3f3f3f;margin-top:5px"><b>Why:</b> ${esc(fp.why)}</div></div>`;});
    else h+=`<p class="small muted">No failure points flagged on this call.</p>`;
    const sg=rp.signature;if(sg&&sg.quote)h+=`<div class="good"><div class="kicker" style="color:var(--teal)">Best moment · ${esc(DN[sg.dim]||'')}</div><div style="margin:3px 0">${esc(sg.label)}</div>${q('Rep',sg.quote,c.recording_url)}</div>`;
    if(rp.demo_lenses){const L=rp.demo_lenses;const rows=Object.entries({demo2win_tell_show_tell:'Tell-Show-Tell (context to impact)',great_demo_last_thing_first:'Last thing first',anti_feature_dump:'Feature-dump check',persona_tailoring:'Persona tailoring'}).filter(([k])=>L[k]).map(([k,lab])=>`<div class="small" style="margin-top:4px"><b>${lab}:</b> ${esc(L[k])}</div>`).join('');if(rows)h+=`<div class="card" style="margin-top:8px"><div class="kicker">The demo, from every lens</div>${rows}</div>`;}
    if((rp.gap_contributions||[]).length){h+=`<div class="card" style="margin-top:8px"><div class="kicker">Buyer concerns raised, and how they were handled</div>`+rp.gap_contributions.map(g=>`<div class="small" style="margin-top:4px"><b>${esc(g.gap)}:</b> <span class="muted">${esc((g.status||'').replace(/_/g,' '))}</span>${g.quote?`, "${esc(g.quote)}"`:''}</div>`).join('')+`</div>`;}
    h+=scoreBreakdown(rp,c.recording_url,true);
    h+=`</div>`;});
  return h;
}
function slugify(s){return (s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}

/* ---------- TECHNICAL WIN ---------- */
function viewTechWin(){
  const o=D.org, tw=o.technical_win||{};
  const deals=D.deals.filter(d=>d.technical_win);
  const TWL={won_written:'Won (written)',won_verbal:'Won (verbal)',in_validation:'In validation',lost_technical:'Lost technical',not_reached:'Not reached',na:'N/A'};
  const TWC={won_written:'var(--c5b)',won_verbal:'var(--c4b)',in_validation:'var(--c3b)',lost_technical:'var(--c1b)',not_reached:'#888',na:'#bbb'};
  let h=`<div class="hero"><div class="eyebrow">Technical Win</div><h1>Did the solution win on the merits, and were the buyer's gaps closed?</h1>
   <p>The Technical Win is the craft-side outcome: the prospect judged the solution superior and the specific gaps they raised were addressed. It is tracked apart from the deal outcome. `;
  if(tw.tw_rate!=null)h+=`Technical win rate <b style="color:var(--c5b)">${Math.round(tw.tw_rate*100)}%</b>`;
  if(tw.business_win_rate!=null)h+=`${tw.tw_rate!=null?' versus':'Business'} business win rate <b>${Math.round(tw.business_win_rate*100)}%</b>`;
  h+=`.</p></div>`;
  if(Object.keys(tw.states||{}).length){h+=`<div class="section"><div class="kicker">Where deals landed technically</div><div class="chips">`;
    Object.entries(tw.states).forEach(([s,n])=>h+=`<span class="chip" style="border-color:${TWC[s]||'#ccc'};color:${TWC[s]||'#555'}">${esc(TWL[s]||s)} · ${n}</span>`);
    h+=`</div></div>`;}
  h+=`<div class="section"><div class="kicker">The gap ledger, deal by deal</div><h2>Every concern the prospect raised, and whether it was closed.</h2>`;
  const GST={addressed_written:['closed, in writing','var(--c5b)'],addressed_verbal:['closed, verbally','var(--c4b)'],acknowledged_open:['open','var(--c3b)'],ignored:['ignored','var(--c1b)']};
  deals.forEach(d=>{const t=d.technical_win||{};const gl=t.gap_ledger||[];
    h+=`<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline"><h3><a class=lnk href="#deal/${esc(d.slug)}">${esc(d.account)}</a></h3><span class="pill" style="background:#f3f3f3;color:${TWC[t.technical_win_state]||'#555'}">${esc(TWL[t.technical_win_state]||t.technical_win_state||'-')}</span></div>`;
    if(t.reached_on&&t.reached_on.quote)h+=`<div class="q rep" style="margin-top:8px">${esc(t.reached_on.quote)}<cite>${esc(t.reached_on.date||'')}</cite></div>`;
    if(gl.length){h+=`<div class="card" style="margin-top:8px;overflow-x:auto"><table><tr><th>Concern raised</th><th>Status</th><th>Evidence</th></tr>`;
      gl.forEach(g=>{const st=GST[g.status]||[g.status,'#888'];h+=`<tr><td>${esc(g.gap)}${g.raised_by?` <span class="tag">${esc(g.raised_by)}</span>`:''}</td><td><b style="color:${st[1]}">${esc(st[0])}</b></td><td class="small muted">${esc((g.evidence&&g.evidence.quote)||'')}</td></tr>`;});
      h+=`</table></div>`;}
    else h+=`<div class="small muted" style="margin-top:6px">No gap ledger recorded.</div>`;
    if(t.platform_claim&&t.platform_claim.flagged)h+=`<div class="small" style="margin-top:6px;color:${t.platform_claim.corroborated?'var(--c5b)':'var(--c2b)'}"><span class="tag">PLATFORM FLAG</span> ${t.platform_claim.corroborated?'corroborated by a call':'not corroborated by any call (claim only)'}. ${esc(t.platform_claim.note||'')}</div>`;
    h+=`</div>`;});
  if(!deals.length)h+=`<p class="muted">No Technical Win records yet.</p>`;
  h+=`</div>`;
  return h;
}
/* ---------- TREND (QoQ) ---------- */
function viewTrend(){
  const q=(D.org.quarters||[]);
  if(!q.length)return `<div class="crumb"><a href="#org">Diagnosis</a> / Trend</div><div class="section"><h2>No quarter-over-quarter trend.</h2><p class="muted">The corpus does not span enough distinct quarters (>=2) to show a trend.</p></div>`;
  let h=`<div class="hero"><div class="eyebrow">Quarter over quarter</div><h1>Craft over time.</h1><p>Mean craft composite per quarter across all scored calls.</p></div><div class="section"><div class="card" style="overflow-x:auto"><table><tr><th>Quarter</th><th>Avg craft</th><th>Calls</th><th></th></tr>`;
  q.forEach(x=>{const[,col]=scColor(x.avg_craft);h+=`<tr><td><b>${esc(x.quarter)}</b></td><td>${sc(x.avg_craft)}</td><td>${x.n}</td><td style="width:220px"><div class="bar"><span style="width:${x.avg_craft/5*100}%;background:${col}"></span></div></td></tr>`;});
  h+=`</table></div></div>`;
  return h;
}

/* ---------- router + search ---------- */
function route(){
  const hash=location.hash.slice(1)||'org';const[v,arg]=hash.split('/');
  let html='';
  if(v==='org')html=viewOrg();
  else if(v==='reps')html=viewReps();
  else if(v==='rep')html=viewRep(arg);
  else if(v==='deals')html=viewDeals();
  else if(v==='deal')html=viewDeal(arg);
  else if(v==='call')html=viewCall(arg);
  else if(v==='crm')html=viewCrm(arg);
  else if(v==='techwin')html=viewTechWin();
  else if(v==='trend')html=viewTrend();
  else if(v==='council')html=viewCouncil();
  else html=viewOrg();
  document.getElementById('app').innerHTML=`<div class="shell">${html}</div>`;
  document.querySelectorAll('.nav a').forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+(['org','reps','deals','techwin','crm','trend','council'].includes(v)?v:'org')));
  window.scrollTo(0,0);
}
window.addEventListener('hashchange',route);

// search index
const SIDX=[];
D.reps.forEach(r=>SIDX.push({k:'Rep',t:r.name,sub:r.archetype,go:'#rep/'+r.slug,s:(r.name+' '+r.archetype).toLowerCase()}));
D.deals.forEach(d=>SIDX.push({k:'Deal',t:d.account,sub:(d.outcome||'')+' · '+money(d.arr),go:'#deal/'+d.slug,s:(d.account+' '+(d.outcome||'')).toLowerCase()}));
D.calls.forEach(c=>SIDX.push({k:'Call',t:c.account+' · '+c.date,sub:(c.title||'').slice(0,50),go:'#call/'+c.call_id,s:(c.account+' '+(c.title||'')+' '+c.date).toLowerCase()}));
function search(term){term=term.trim().toLowerCase();const box=document.getElementById('results');if(!term){box.style.display='none';return;}
  const hits=SIDX.filter(x=>x.s.includes(term)).slice(0,30);
  box.innerHTML=hits.length?hits.map((h,i)=>`<a href="${h.go}" data-i="${i}"><span class="k">${h.k}</span>${esc(h.t)} <span class="muted small">${esc(h.sub)}</span></a>`).join(''):'<a class="muted">no matches</a>';
  box.style.display='block';
  box.querySelectorAll('a[href]').forEach(a=>a.onclick=()=>{box.style.display='none';document.getElementById('q').value='';});}
document.addEventListener('DOMContentLoaded',()=>{
  const q=document.getElementById('q');q.addEventListener('input',()=>search(q.value));
  q.addEventListener('keydown',e=>{if(e.key==='Escape'){document.getElementById('results').style.display='none';q.blur();}});
  document.addEventListener('click',e=>{if(!e.target.closest('.searchwrap'))document.getElementById('results').style.display='none';});
  route();
});
"""

def main():
    wd = A.workdir(); cfg = A.load_config(wd)
    org = cfg.get("org_name", "")
    rdate = os.environ.get("REPORT_DATE", "")
    data = A.read_json(os.path.join(wd, "analysis", "report_data.json"))
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{html.escape(org)} presales audit</title>
<style>{CSS}</style></head><body>
<div class="top"><div class="shell">
  <span class="brand">{html.escape(org)} presales audit</span>
  <div class="nav"><a href="#org">Diagnosis</a><a href="#reps">Engineers</a><a href="#deals">Deals</a><a href="#techwin">Technical Win</a><a href="#crm">Trust check</a><a href="#trend">Trend</a><a href="#council">Council</a></div>
  <div class="searchwrap"><input id="q" placeholder="Search reps, deals, calls..." autocomplete=off><div id="results"></div></div>
</div></div>
<div id="app"></div>
<footer><div class="shell">{html.escape(org)} per-call presales audit · craft, technical win, and business outcome kept separate · {html.escape(rdate)}. Numbers aggregate; open any call to see how the read was made.</div></footer>
<script id="DATA" type="application/json">{blob}</script>
<script>{JS}</script>
</body></html>"""
    fp = os.path.join(wd, "report.html")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"== report_app: {len(page)//1024} KB -> {fp}")

if __name__ == "__main__":
    main()
