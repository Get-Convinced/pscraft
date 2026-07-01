"""Shared plumbing for call-craft. Stdlib only. Structure, never meaning.

A function here may parse a file, map a column by synonym, split a transcript into turns, join on
ids, count, or read/write JSON. It must NEVER score a call, classify a call by keyword, or decide a
rep's role — that is the model's job (see prompts/).
"""
import os
import re
import csv
import sys
import json
import glob
import html as _html
from datetime import datetime, date

# ---------------------------------------------------------------------------- run dir + config

def workdir():
    wd = None
    argv = sys.argv
    for i, a in enumerate(argv):
        if a == "--workdir" and i + 1 < len(argv):
            wd = argv[i + 1]
        elif a.startswith("--workdir="):
            wd = a.split("=", 1)[1]
    wd = wd or os.environ.get("AUDIT_WORKDIR")
    if not wd:
        sys.exit("ERROR: set AUDIT_WORKDIR or pass --workdir=/abs/path")
    wd = os.path.abspath(os.path.expanduser(wd))
    if not os.path.isdir(wd):
        sys.exit(f"ERROR: workdir does not exist: {wd}")
    return wd


def load_config(wd):
    p = os.path.join(wd, "config.json")
    if not os.path.exists(p):
        sys.exit(f"ERROR: no config.json in {wd} (copy schema/config.template.json and fill it)")
    cfg = _strip_doc(read_json(p))
    return cfg


def _strip_doc(o):
    """Drop _doc / _*_doc / _example helper keys so config reads clean."""
    if isinstance(o, dict):
        return {k: _strip_doc(v) for k, v in o.items()
                if not (k == "_doc" or k.startswith("_") and k.endswith(("_doc", "_example", "_note")))}
    if isinstance(o, list):
        return [_strip_doc(x) for x in o]
    return o


def load_rubric(skill_dir, cfg):
    base = read_json(os.path.join(skill_dir, "schema", "rubric.template.json"))
    base = _strip_doc(base)
    overrides = (cfg.get("rubric") or {}).get("overrides") or {}
    return deep_merge(base, overrides)


def deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------- json io

def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ensure_dirs(wd):
    for d in ("canonical", "analysis", "reports"):
        os.makedirs(os.path.join(wd, d), exist_ok=True)


# ---------------------------------------------------------------------------- csv synonym mapping

def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def resolve_columns(header, colmap):
    """colmap: {canonical: [synonym, ...]}. Returns {canonical: actual_header or None}."""
    lower = {h.lower().strip(): h for h in header}
    out = {}
    for canon, syns in colmap.items():
        found = None
        for s in syns:
            if s in header:
                found = s; break
            if s.lower().strip() in lower:
                found = lower[s.lower().strip()]; break
        out[canon] = found
    return out


def get(row, resolved, canon, default=""):
    col = resolved.get(canon)
    if not col:
        return default
    v = row.get(col)
    return (v if v is not None else default)


# ---------------------------------------------------------------------------- dates / domains / slug

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def emails_in(text):
    return [e.lower() for e in _EMAIL.findall(text or "")]


def domain_of(email):
    return email.split("@", 1)[1].lower() if "@" in email else ""


def is_org_email(email, org_domains):
    d = domain_of(email)
    return any(d == od.lower() or d.endswith("." + od.lower()) for od in org_domains)


def parse_date(s):
    """Best-effort date parse → 'YYYY-MM-DD' or None. Tries several common CRM/transcript formats."""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for fmt in ("%d/%m/%Y %I:%M %p", "%d/%m/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
                "%Y/%m/%d", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def month_of(d):
    return d[:7] if d and len(d) >= 7 else None


def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").strip().lower())
    return s.strip("-") or "x"


def norm_name(s):
    """Normalize a display name for fuzzy consolidation (lowercase, dedupe repeated tokens)."""
    s = re.sub(r"\(.*?\)", " ", s or "")
    s = re.sub(r"[^A-Za-z ]+", " ", s).lower()
    toks = [t for t in s.split() if t]
    seen, out = set(), []
    for t in toks:               # collapse "sahil gupta sahil gupta" -> "sahil gupta"
        if t not in seen:
            seen.add(t); out.append(t)
    return " ".join(out)


def esc(s):
    return _html.escape(str(s) if s is not None else "")


def canonical_rep_name(name, cfg):
    """Resolve a rep display name to its canonical form via config.roles.name_fixes (handles
    diarization fragments + spelling variants). Returns the canonical name (or the input)."""
    roles = cfg.get("roles") or {}
    n = norm_name(name)
    for nf in (roles.get("name_fixes") or []):
        variants = {norm_name(v) for v in (nf.get("variants") or [])}
        cn = nf.get("canonical_name")
        if cn and (n in variants or n == norm_name(cn)):
            return cn
    return name


def excluded_rep(name, cfg):
    """True if this rep should be dropped from analysis/report. Canonicalizes via name_fixes first,
    then matches the FULL normalized name (or email) against config.roles.exclude_from_report.
    NOTE: no first-name-token matching — that would erase everyone sharing a first name with an
    excluded person. Add bare fragments (e.g. 'Ravi') to name_fixes to fold them onto the full name."""
    roles = cfg.get("roles") or {}
    excl = roles.get("exclude_from_report") or []
    n = norm_name(canonical_rep_name(name, cfg))
    if not n:
        return False
    full = {norm_name(x) for x in excl}
    return n in full


# ---------------------------------------------------------------------------- account identity
# The account analog of roles.name_fixes. Two problems these solve, both common on partner/reseller
# (channel) deals where the end customer is sold THROUGH a system integrator:
#   1. spelling/legal-suffix drift ("Sekisui" / "Sekisui Chemical" / "SekiSui Chemicals") splits one
#      opportunity across three account keys.
#   2. the account-naming model labels a call by the dominant speaker's company (the partner) instead
#      of the end customer, so e.g. a Sekisui deal call gets filed under "Tech Mahindra".
# (1) is fixed org-wide by config.account_aliases; (2) is fixed per-call by config.call_company_overrides
# (a partner can have OTHER genuine calls, so reassignment must be call-scoped, never company-wide).

_ACCT_SUFFIX = re.compile(r"\b(pvt|private|limited|ltd|inc|llc|llp|plc|gmbh|corp|corporation|co|company|"
                          r"group|industries|industry|technologies|technology|solutions|systems|global|"
                          r"international|india|enterprises|holdings|services)\b", re.I)


def canonical_account(name, cfg):
    """Resolve an account/company name to its canonical display form via config.account_aliases.
    Each alias is {canonical, variants:[...]}; match is on the normalized (suffix-stripped) form so
    'SekiSui Chemicals' and 'Sekisui' both fold onto the one canonical 'Sekisui Chemical'."""
    if not name:
        return name
    n = _norm_account_raw(name)
    for a in (cfg.get("account_aliases") or []):
        cn = a.get("canonical")
        variants = {_norm_account_raw(v) for v in (a.get("variants") or [])}
        if cn and (n in variants or n == _norm_account_raw(cn)):
            return cn
    return name


def _norm_account_raw(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _ACCT_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_account(s, cfg=None):
    """Account grouping key. Applies account_aliases first (when cfg given) so every spelling of one
    company collapses to a single key, then strips legal suffixes/punctuation."""
    if cfg is not None:
        s = canonical_account(s, cfg)
    return _norm_account_raw(s)


def excluded_account(name, cfg):
    """True if this account should be dropped from the report entirely (config.exclude_accounts):
    advisory/consulting/partner firms that aren't real buying accounts (e.g. Grant Thornton).
    Alias-aware, so every spelling of the excluded account is caught."""
    excl = {_norm_account_raw(x) for x in (cfg.get("exclude_accounts") or [])}
    return bool(excl) and norm_account(name, cfg) in excl


def load_call_company(wd, cfg=None):
    """Read analysis/call_company.json and apply config.call_company_overrides on the way out.
    Each override is {call_id, company?, bucket?, call_phase?, ...}; listed fields are merged onto the
    record (creating one if the namer skipped the call). This is the single source every consumer
    reads through, so a reassignment lands in linking, scoring, roster, and the report at once."""
    p = os.path.join(wd, "analysis", "call_company.json")
    cc = read_json(p) if os.path.exists(p) else {}
    if not isinstance(cc, dict):
        cc = {c.get("call_id"): c for c in cc if isinstance(c, dict) and c.get("call_id")}
    for ov in ((cfg or {}).get("call_company_overrides") or []):
        cid = ov.get("call_id")
        if not cid:
            continue
        rec = dict(cc.get(cid) or {"call_id": cid})
        for k, v in ov.items():
            if k in ("call_id", "note"):
                continue
            rec[k] = v
        rec.setdefault("call_status", "live")
        rec.setdefault("transcript_quality", "fair")
        cc[cid] = rec
    return cc


# ---------------------------------------------------------------------------- transcript parsing

def parse_transcript_file(path):
    """Dispatch by extension. Returns a canonical call dict or None if unparseable.
    Canonical: {call_id, title, date, platform, duration_min, recording_url,
                header_emails, attendees, turns:[{speaker, t, text}], speakers:[...], n_turns}
    """
    ext = os.path.splitext(path)[1].lower()
    raw = _read_text(path)
    if ext == ".json":
        return _parse_readai_json(path, raw)
    if ext in (".vtt", ".srt"):
        return _parse_caption(path, raw, ext)
    # .md / .txt / anything speaker-labelled
    return _parse_md(path, raw)


def _read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


_TURN = re.compile(r"^\*\*(?P<spk>[^*]+?)\*\*\s*(?:\[(?P<t>[^\]]*)\])?\s*:\s*(?P<txt>.*)$")
_HDR = re.compile(r"^-\s*\*\*(?P<k>[^*]+?):\*\*\s*(?P<v>.*)$")


def _parse_md(path, raw):
    stem = os.path.splitext(os.path.basename(path))[0]
    lines = raw.splitlines()
    title = None
    header = {}
    body_start = 0
    for i, ln in enumerate(lines):
        if title is None and ln.startswith("# "):
            title = ln[2:].strip()
        m = _HDR.match(ln.strip())
        if m:
            header[m.group("k").strip().lower()] = m.group("v").strip()
        if ln.strip().lower().startswith("## transcript"):
            body_start = i + 1
            break
    # turns
    turns = []
    cur = None
    for ln in lines[body_start:]:
        if ln.startswith("## "):  # any further section ends transcript
            if cur:
                turns.append(cur); cur = None
            continue
        m = _TURN.match(ln.strip())
        if m:
            if cur:
                turns.append(cur)
            cur = {"speaker": m.group("spk").strip(), "t": (m.group("t") or "").strip(),
                   "text": m.group("txt").strip()}
        elif cur is not None and ln.strip():
            cur["text"] += " " + ln.strip()
    if cur:
        turns.append(cur)

    # header-derived facts
    date_str = None
    for k in ("date/time (ist)", "date/time", "date", "start time"):
        if k in header:
            date_str = parse_date(header[k]); break
    if not date_str:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
        date_str = m.group(1) if m else None
    call_id = header.get("meeting id") or stem
    rec = None
    for k in ("report", "recording", "report url", "link"):
        if k in header:
            rec = header[k]; break
    dur = None
    if "duration" in header:
        mm = re.search(r"(\d+)", header["duration"])
        dur = int(mm.group(1)) if mm else None
    header_emails = emails_in(raw[:4000])
    attendees = []
    if "attended" in header:
        attendees = [a.strip() for a in re.split(r"[,;]", header["attended"]) if a.strip()]
    speakers = sorted({t["speaker"] for t in turns if t["speaker"]})
    if not turns:
        return None
    return {"call_id": call_id, "source_file": os.path.basename(path), "title": title or stem,
            "date": date_str, "platform": header.get("platform"), "duration_min": dur,
            "recording_url": rec, "header_emails": header_emails, "attendees": attendees,
            "turns": turns, "speakers": speakers, "n_turns": len(turns)}


def _parse_readai_json(path, raw):
    try:
        d = json.loads(raw)
    except Exception:
        return None
    tr = d.get("transcript") or {}
    turns = []
    for t in (tr.get("turns") or []):
        spk = t.get("speaker") or t.get("speaker_name") or t.get("name") or ""
        txt = t.get("text") or t.get("words") or ""
        turns.append({"speaker": str(spk).strip(), "t": str(t.get("start_time") or t.get("ts") or ""),
                      "text": str(txt).strip()})
    parts = d.get("participants") or []
    header_emails = [p.get("email", "").lower() for p in parts if p.get("email")]
    attendees = [p.get("name") for p in parts if p.get("attended") and p.get("name")]
    start = d.get("start_time_ms")
    date_str = None
    if start:
        try:
            date_str = datetime.utcfromtimestamp(start / 1000).strftime("%Y-%m-%d")
        except Exception:
            pass
    if not turns:
        return None
    return {"call_id": d.get("id") or os.path.splitext(os.path.basename(path))[0],
            "source_file": os.path.basename(path), "title": d.get("title") or "",
            "date": date_str, "platform": d.get("platform"),
            "duration_min": None, "recording_url": d.get("report_url"),
            "header_emails": header_emails, "attendees": attendees,
            "turns": turns, "speakers": sorted({t["speaker"] for t in turns if t["speaker"]}),
            "n_turns": len(turns)}


def _parse_caption(path, raw, ext):
    stem = os.path.splitext(os.path.basename(path))[0]
    turns = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        txt = " ".join(l for l in lines if "-->" not in l and not l.strip().isdigit()
                       and not l.strip().startswith("WEBVTT"))
        if txt.strip():
            turns.append({"speaker": "", "t": "", "text": txt.strip()})
    if not turns:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    return {"call_id": stem, "source_file": os.path.basename(path), "title": stem,
            "date": m.group(1) if m else None, "platform": None, "duration_min": None,
            "recording_url": None, "header_emails": [], "attendees": [],
            "turns": turns, "speakers": [], "n_turns": len(turns)}


def transcript_text(call, max_chars=None):
    """Reconstruct the readable transcript for a model. Header + turns."""
    head = [f"# {call.get('title','')}", f"Date: {call.get('date','')}  Platform: {call.get('platform','')}",
            f"Attendees: {', '.join(call.get('attendees') or [])}",
            f"Emails: {', '.join(call.get('header_emails') or [])}",
            f"Recording: {call.get('recording_url') or 'no link'}", "", "## Transcript"]
    body = [f"**{t['speaker']}** [{t['t']}]: {t['text']}" if t['speaker'] else t['text']
            for t in call.get("turns", [])]
    out = "\n".join(head + body)
    if max_chars and len(out) > max_chars:
        # keep a head+tail window: the close of a sales call (next steps, commitments, urgency)
        # is as important as the open, so never drop the end.
        h = int(max_chars * 0.6); t = max_chars - h - 24
        out = out[:h] + "\n...[middle of call truncated]...\n" + out[-t:]
    return out
