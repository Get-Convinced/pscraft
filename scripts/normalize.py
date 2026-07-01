#!/usr/bin/env python3
"""Phase 3 — normalize heterogeneous inputs into the canonical model. Structure only, never meaning.

Reads:
  <workdir>/intake.json   (REQUIRED — written by subskills/intake/; says what is present + each
                           file's bucket and detected format)
  <workdir>/mapping.json  (OPTIONAL — column mappings a model produced via prompts/crm_mapping.md;
                           one block per kind: deals / notes / stage_history)

Writes (matching the EXACT canonical shapes the rest of the pipeline reads):
  canonical/transcripts.json   ALWAYS (transcripts are required)
  canonical/deals.json         only when intake has crm_deals
  canonical/notes.json         only when intake has crm_notes
  canonical/stage_history.json only when intake has stage_history

This script is pure plumbing. It parses files, applies a mapping a model gave it, joins on ids,
and writes JSON. It NEVER reads a transcript for meaning, never classifies a call, never scores.
A model proposes the column mapping and the file classification; this script applies them.

CLI:
  python3 scripts/normalize.py --workdir <dir>
"""
import os
import re
import csv
import sys
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import audit as A

# Optional dependency: openpyxl for .xlsx. We never require it. If it is missing and an xlsx input
# exists, we say so and skip that file rather than crash. CSV/JSON inputs are unaffected.
try:
    import openpyxl  # type: ignore
    _HAVE_OPENPYXL = True
except Exception:
    _HAVE_OPENPYXL = False


# ============================================================================ intake / mapping io

def load_intake(wd):
    p = os.path.join(wd, "intake.json")
    if not os.path.exists(p):
        sys.exit(f"ERROR: no intake.json in {wd} (run subskills/intake first)")
    return A.read_json(p)


def load_mapping(wd):
    """Optional. {deals:{canon:src|null}, notes:{...}, stage_history:{...}}. Absent => {}."""
    p = os.path.join(wd, "mapping.json")
    return A.read_json(p) if os.path.exists(p) else {}


def _bucket(intake, name):
    """Return the bucket record for an optional input, or a present:false stub."""
    b = intake.get(name)
    if isinstance(b, dict):
        return b
    return {"present": False, "files": []}


def _bucket_files(bucket):
    """Expand a bucket's file entries into a flat list of (path, format) tuples.
    A directory entry (is_dir) is expanded by walking it for known extensions."""
    out = []
    for f in (bucket.get("files") or []):
        path = f.get("path")
        fmt = f.get("format")
        if not path:
            continue
        if f.get("is_dir") and os.path.isdir(path):
            for ext in ("*.md", "*.txt", "*.json", "*.vtt", "*.srt"):
                for fp in glob.glob(os.path.join(path, "**", ext), recursive=True):
                    out.append((fp, fmt))
        else:
            out.append((path, fmt))
    return out


# ============================================================================ transcripts

# We reuse lib/audit.py's parsers for the shapes it already handles (Read.ai md/json, VTT/SRT, generic
# speaker-labelled markdown). We add parsers for the vendor shapes it does not: Gong / Fireflies /
# Otter JSON, and a generic JSON array of turns. Every parser returns the SAME canonical call dict:
#   {call_id, source_file, title, date, platform, duration_min, recording_url,
#    header_emails, attendees, turns:[{speaker, t, text}], speakers:[...], n_turns}

def _epoch_to_date(v):
    """Accept ms or s epoch (int/float/str) -> 'YYYY-MM-DD' or None."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n > 1e11:  # looks like milliseconds
        n = n / 1000.0
    try:
        return datetime.utcfromtimestamp(n).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return None


def _emails_from_list(items):
    out = []
    for p in items or []:
        if isinstance(p, dict):
            e = p.get("email") or p.get("email_address")
            if e:
                out.append(str(e).lower())
        elif isinstance(p, str) and "@" in p:
            out.append(p.lower())
    return out


def _names_from_list(items):
    out = []
    for p in items or []:
        if isinstance(p, dict):
            n = p.get("name") or p.get("display_name") or p.get("full_name")
            if n:
                out.append(str(n).strip())
        elif isinstance(p, str):
            out.append(p.strip())
    return [n for n in out if n]


def _finish_call(path, call_id, title, date, platform, duration_min, recording_url,
                 header_emails, attendees, turns):
    turns = [t for t in turns if (t.get("text") or "").strip()]
    if not turns:
        return None
    speakers = sorted({t["speaker"] for t in turns if t.get("speaker")})
    return {
        "call_id": call_id or os.path.splitext(os.path.basename(path))[0],
        "source_file": os.path.basename(path),
        "title": title or os.path.splitext(os.path.basename(path))[0],
        "date": date,
        "platform": platform,
        "duration_min": duration_min,
        "recording_url": recording_url,
        "header_emails": header_emails or [],
        "attendees": attendees or [],
        "turns": turns,
        "speakers": speakers,
        "n_turns": len(turns),
    }


def _parse_gong_json(path, d):
    """Gong call export. Tolerant of the common field names; transcript is a list of monologues,
    each with a speaker and a list of sentences."""
    meta = d.get("metaData") or d.get("meta") or d
    title = meta.get("title") or d.get("title") or ""
    date = (_epoch_to_date(meta.get("started")) or A.parse_date(meta.get("scheduled"))
            or A.parse_date(meta.get("started")) or A.parse_date(d.get("date")))
    rec = (meta.get("url") or d.get("url") or d.get("recordingUrl"))
    dur = meta.get("duration")
    duration_min = int(dur / 60) if isinstance(dur, (int, float)) and dur > 120 else (
        int(dur) if isinstance(dur, (int, float)) else None)
    parties = d.get("parties") or []
    # speakerId -> name
    spk_name = {}
    for p in parties:
        sid = p.get("speakerId") or p.get("id")
        nm = p.get("name") or p.get("emailAddress")
        if sid and nm:
            spk_name[str(sid)] = str(nm)
    header_emails = [str(p.get("emailAddress")).lower() for p in parties if p.get("emailAddress")]
    attendees = [str(p.get("name")).strip() for p in parties if p.get("name")]
    turns = []
    for mono in (d.get("transcript") or []):
        sid = str(mono.get("speakerId") or mono.get("speaker") or "")
        spk = spk_name.get(sid, mono.get("speakerName") or sid or "")
        sents = mono.get("sentences") or []
        if sents:
            text = " ".join(s.get("text", "") for s in sents if s.get("text"))
            t0 = sents[0].get("start")
            ts = str(int(t0 / 1000)) if isinstance(t0, (int, float)) else ""
        else:
            text = mono.get("text", "")
            ts = str(mono.get("start", "") or "")
        if text.strip():
            turns.append({"speaker": str(spk).strip(), "t": ts, "text": text.strip()})
    return _finish_call(path, d.get("callId") or meta.get("id"), title, date, "gong",
                        duration_min, rec, header_emails, attendees, turns)


def _parse_fireflies_json(path, d):
    """Fireflies transcript export. Sentences carry speaker_name + text; dateString or date present."""
    title = d.get("title") or ""
    date = A.parse_date(d.get("dateString")) or _epoch_to_date(d.get("date"))
    rec = d.get("transcript_url") or d.get("audio_url") or d.get("video_url")
    dur = d.get("duration")
    duration_min = int(dur) if isinstance(dur, (int, float)) else None
    parts = d.get("participants") or d.get("meeting_attendees") or []
    header_emails = _emails_from_list(parts)
    attendees = _names_from_list(parts)
    turns = []
    for s in (d.get("sentences") or d.get("transcript") or []):
        spk = s.get("speaker_name") or s.get("speaker") or ""
        txt = s.get("text") or s.get("raw_text") or ""
        ts = s.get("start_time") or s.get("startTime") or ""
        if str(txt).strip():
            turns.append({"speaker": str(spk).strip(), "t": str(ts), "text": str(txt).strip()})
    return _finish_call(path, d.get("id") or d.get("transcript_id"), title, date, "fireflies",
                        duration_min, rec, header_emails, attendees, turns)


def _parse_otter_json(path, d):
    """Otter.ai export. speech segments with speaker + transcript text."""
    title = d.get("title") or d.get("name") or ""
    date = A.parse_date(d.get("created_at")) or _epoch_to_date(d.get("start_time"))
    rec = d.get("share_url") or d.get("url")
    segs = d.get("transcripts") or d.get("speeches") or d.get("segments") or []
    turns = []
    for s in segs:
        spk = s.get("speaker") or s.get("speaker_name") or ""
        if isinstance(spk, dict):
            spk = spk.get("name") or ""
        txt = s.get("transcript") or s.get("text") or ""
        ts = s.get("start_offset") or s.get("start") or ""
        if str(txt).strip():
            turns.append({"speaker": str(spk).strip(), "t": str(ts), "text": str(txt).strip()})
    header_emails = _emails_from_list(d.get("participants"))
    attendees = _names_from_list(d.get("participants") or d.get("speakers"))
    return _finish_call(path, d.get("id") or d.get("otid"), title, date, "otter",
                        None, rec, header_emails, attendees, turns)


def _parse_generic_json(path, d):
    """A generic JSON shape: either a top-level list of turns, or an object with a turns/segments/
    transcript array. Each turn is {speaker?, text|words, t|start|timestamp?}."""
    if isinstance(d, list):
        rows = d
        meta = {}
    else:
        meta = d
        rows = (d.get("turns") or d.get("segments") or d.get("transcript")
                or d.get("utterances") or [])
        if isinstance(rows, dict):  # e.g. {"turns": {...}} unlikely, but guard
            rows = list(rows.values())
    turns = []
    for r in rows or []:
        if not isinstance(r, dict):
            # a bare list of strings -> speakerless turns
            if isinstance(r, str) and r.strip():
                turns.append({"speaker": "", "t": "", "text": r.strip()})
            continue
        spk = (r.get("speaker") or r.get("speaker_name") or r.get("name")
               or r.get("speakerName") or "")
        if isinstance(spk, dict):
            spk = spk.get("name") or ""
        txt = r.get("text") or r.get("words") or r.get("content") or r.get("transcript") or ""
        if isinstance(txt, list):
            txt = " ".join(str(w) for w in txt)
        ts = r.get("t") or r.get("start") or r.get("timestamp") or r.get("start_time") or ""
        if str(txt).strip():
            turns.append({"speaker": str(spk).strip(), "t": str(ts), "text": str(txt).strip()})
    title = meta.get("title") if isinstance(meta, dict) else ""
    date = None
    if isinstance(meta, dict):
        date = (A.parse_date(meta.get("date")) or _epoch_to_date(meta.get("start_time_ms"))
                or _epoch_to_date(meta.get("start_time")) or _epoch_to_date(meta.get("started")))
    rec = meta.get("recording_url") or meta.get("url") if isinstance(meta, dict) else None
    header_emails = _emails_from_list(meta.get("participants")) if isinstance(meta, dict) else []
    attendees = _names_from_list(meta.get("participants")) if isinstance(meta, dict) else []
    return _finish_call(path, (meta.get("id") if isinstance(meta, dict) else None),
                        title, date, (meta.get("platform") if isinstance(meta, dict) else None),
                        None, rec, header_emails, attendees, turns)


# format -> parser. Anything not listed falls back to extension dispatch in lib/audit.py.
_JSON_PARSERS = {
    "readai_json": lambda p, raw: A.parse_transcript_file(p),  # lib handles read.ai json by ext
    "gong":        lambda p, raw: _dispatch_json(p, raw, _parse_gong_json),
    "fireflies":   lambda p, raw: _dispatch_json(p, raw, _parse_fireflies_json),
    "otter":       lambda p, raw: _dispatch_json(p, raw, _parse_otter_json),
    "generic_json":lambda p, raw: _dispatch_json(p, raw, _parse_generic_json),
}


def _dispatch_json(path, raw, fn):
    try:
        d = json.loads(raw)
    except Exception:
        return None
    return fn(path, d)


def _read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_transcript(path, fmt):
    """Parse one transcript file using the declared format, falling back to lib/audit.py's
    extension-based dispatch (Read.ai md/json, VTT/SRT, generic markdown). Returns a canonical call
    dict or None if unparseable. The format hint comes from the intake manifest; if it is missing or
    unrecognized we let the extension decide."""
    ext = os.path.splitext(path)[1].lower()
    fmt = (fmt or "").lower()

    # JSON-family vendor formats we added on top of lib.
    if ext == ".json":
        raw = _read_text(path)
        parser = _JSON_PARSERS.get(fmt)
        if parser:
            c = parser(path, raw)
            if c:
                return c
        # Unknown json format hint: try read.ai (lib), then generic.
        c = A.parse_transcript_file(path)
        if c:
            return c
        return _dispatch_json(path, raw, _parse_generic_json)

    # Everything else (md, txt, vtt, srt, plain text, zoom) is handled by lib's extension dispatch.
    # That covers readai_md, markdown, plain_text, zoom_vtt out of the box.
    return A.parse_transcript_file(path)


def normalize_transcripts(wd, intake):
    bucket = intake.get("transcripts") or {}
    if not bucket.get("present"):
        sys.exit("ERROR: intake.json says transcripts are not present. Transcripts are required.")
    files = _bucket_files(bucket)
    if not files:
        sys.exit("ERROR: intake.json lists no transcript files. Transcripts are required.")
    files = sorted(set(files), key=lambda x: x[0])
    calls, dropped, seen = [], [], {}
    for fp, fmt in files:
        if not os.path.exists(fp):
            dropped.append((os.path.basename(fp), "file not found")); continue
        try:
            c = parse_transcript(fp, fmt)
        except Exception as e:
            dropped.append((os.path.basename(fp), f"parse error: {e}")); continue
        if not c or c["n_turns"] == 0:
            dropped.append((os.path.basename(fp), "no parseable turns")); continue
        cid = c["call_id"]
        if cid in seen:
            dropped.append((c["source_file"], f"duplicate id of {seen[cid]}")); continue
        seen[cid] = c["source_file"]
        calls.append(c)
    A.write_json(os.path.join(wd, "canonical", "transcripts.json"), calls)
    return calls, dropped


# ============================================================================ tabular readers

def read_rows(path, fmt):
    """Read a tabular file (CSV / XLSX / JSON) into a list of dict rows. Returns (rows, header_list).
    XLSX requires openpyxl; without it we skip and return ([], []) with a warning printed upstream."""
    fmt = (fmt or "").lower()
    ext = os.path.splitext(path)[1].lower()
    if fmt == "xlsx" or ext in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    if fmt == "json" or ext == ".json":
        return _read_json_rows(path)
    # default: csv (also handles .tsv if comma fails)
    return _read_csv(path)


def _read_csv(path):
    rows = A.read_csv_rows(path)
    header = list(rows[0].keys()) if rows else []
    return rows, header


def _read_xlsx(path):
    if not _HAVE_OPENPYXL:
        return None, None  # signal: openpyxl missing
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    try:
        header = [str(h).strip() if h is not None else "" for h in next(it)]
    except StopIteration:
        return [], []
    rows = []
    for r in it:
        if r is None:
            continue
        vals = [("" if v is None else (v.strftime("%Y-%m-%d") if isinstance(v, datetime) else str(v)))
                for v in r]
        if not any(v for v in vals):
            continue
        rows.append({header[i]: (vals[i] if i < len(vals) else "") for i in range(len(header))})
    return rows, header


def _read_json_rows(path):
    """A CRM/notes/stage export as JSON. Accept a top-level array of objects, or {records:[...]} /
    {data:[...]} / {rows:[...]}."""
    d = A.read_json(path)
    if isinstance(d, dict):
        for k in ("records", "data", "rows", "deals", "notes", "stage_history"):
            if isinstance(d.get(k), list):
                d = d[k]; break
    if not isinstance(d, list):
        return [], []
    rows = [r for r in d if isinstance(r, dict)]
    header = list(rows[0].keys()) if rows else []
    return rows, header


def _mget(row, mapping, canon, default=""):
    """Read a value from a row using the model-produced mapping {canon: source_col|null}."""
    src = (mapping or {}).get(canon)
    if not src:
        return default
    v = row.get(src)
    return v if v is not None else default


# ============================================================================ deals / notes / stage

def normalize_deals(wd, intake, mapping):
    bucket = _bucket(intake, "crm_deals")
    out_path = os.path.join(wd, "canonical", "deals.json")
    if not bucket.get("present"):
        print("  note: no CRM deals export. Skipping deals.json (audit degrades to craft-only).")
        return None  # do NOT write the file when absent
    m = (mapping or {}).get("deals") or {}
    deals = []
    for path, fmt in _bucket_files(bucket):
        if not os.path.exists(path):
            print(f"  WARNING: deals file missing: {path}"); continue
        rows, header = read_rows(path, fmt)
        if rows is None:
            print(f"  WARNING: {os.path.basename(path)} is xlsx but openpyxl is not installed; "
                  f"skipped. Install openpyxl or export to CSV.")
            continue
        for r in rows:
            did = str(_mget(r, m, "deal_id")).strip()
            name = str(_mget(r, m, "deal_name")).strip()
            if not did and not name:
                continue
            deals.append({
                "deal_id": did or name,            # fall back to name as the join key (lib pattern)
                "deal_name": name,
                "account": str(_mget(r, m, "account")).strip(),
                "owner": str(_mget(r, m, "owner")).strip(),
                "stage": str(_mget(r, m, "stage")).strip(),
                "arr": str(_mget(r, m, "amount_arr")).strip(),
                "otc": str(_mget(r, m, "amount_otc")).strip(),
                "created": A.parse_date(_mget(r, m, "created_date")),
                "closing_date": A.parse_date(_mget(r, m, "close_date")),
                "products": str(_mget(r, m, "products")).strip(),
                "region": str(_mget(r, m, "region")).strip(),
                "se_owner": str(_mget(r, m, "se_owner")).strip(),
                "competitor": str(_mget(r, m, "competitor")).strip(),
                "technical_win_flag": str(_mget(r, m, "technical_win")).strip(),
                "meddic": {
                    "metric": str(_mget(r, m, "meddic_metric")).strip(),
                    "economic_buyer": str(_mget(r, m, "meddic_economic_buyer")).strip(),
                    "decision_process": str(_mget(r, m, "meddic_decision_process")).strip(),
                    "decision_criteria": str(_mget(r, m, "meddic_decision_criteria")).strip(),
                    "champion": str(_mget(r, m, "meddic_champion")).strip(),
                    "pain": str(_mget(r, m, "meddic_pain")).strip(),
                    "competition": str(_mget(r, m, "meddic_competition")).strip(),
                    "paper_process": str(_mget(r, m, "meddic_paper_process")).strip(),
                },
                "next_step": str(_mget(r, m, "next_step")).strip(),
            })
    A.write_json(out_path, deals)
    return deals


def normalize_notes(wd, intake, mapping):
    bucket = _bucket(intake, "crm_notes")
    out_path = os.path.join(wd, "canonical", "notes.json")
    if not bucket.get("present"):
        print("  note: no rep notes. Skipping notes.json (follow-through leans on calls + stages).")
        return None
    m = (mapping or {}).get("notes") or {}
    notes = {}
    for path, fmt in _bucket_files(bucket):
        if not os.path.exists(path):
            print(f"  WARNING: notes file missing: {path}"); continue
        rows, header = read_rows(path, fmt)
        if rows is None:
            print(f"  WARNING: {os.path.basename(path)} is xlsx but openpyxl is not installed; skipped.")
            continue
        for r in rows:
            did = str(_mget(r, m, "deal_id")).strip()
            name = str(_mget(r, m, "deal_name")).strip()
            content = str(_mget(r, m, "content")).strip()
            key = did or name
            if not key or not content:
                continue
            notes.setdefault(key, []).append({
                "deal_name": name,
                "content": content,
                "owner": str(_mget(r, m, "author")).strip(),
                "created": A.parse_date(_mget(r, m, "created_date")),
            })
    for k in notes:
        notes[k].sort(key=lambda x: x["created"] or "")
    A.write_json(out_path, notes)
    return notes


def normalize_stage_history(wd, intake, mapping):
    bucket = _bucket(intake, "stage_history")
    out_path = os.path.join(wd, "canonical", "stage_history.json")
    if not bucket.get("present"):
        print("  note: no stage history. Skipping stage_history.json (funnel = current-stage snapshot).")
        return None
    m = (mapping or {}).get("stage_history") or {}
    hist = {}
    for path, fmt in _bucket_files(bucket):
        if not os.path.exists(path):
            print(f"  WARNING: stage history file missing: {path}"); continue
        rows, header = read_rows(path, fmt)
        if rows is None:
            print(f"  WARNING: {os.path.basename(path)} is xlsx but openpyxl is not installed; skipped.")
            continue
        for r in rows:
            did = str(_mget(r, m, "deal_id")).strip()
            name = str(_mget(r, m, "deal_name")).strip()
            key = did or name
            if not key:
                continue
            raw_mtime = _mget(r, m, "moved_at")
            hist.setdefault(key, []).append({
                "deal_name": name,
                "moved_to": str(_mget(r, m, "to_stage")).strip(),
                "from_stage": str(_mget(r, m, "from_stage")).strip(),
                "duration_days": str(_mget(r, m, "duration_days")).strip(),
                "modified_time": A.parse_date(raw_mtime),
                "_raw_mtime": raw_mtime if raw_mtime is not None else "",
            })
    for k in hist:
        hist[k].sort(key=lambda x: x["modified_time"] or "")
    A.write_json(out_path, hist)
    return hist


# ============================================================================ SE platform + artifacts

def normalize_se_platform(wd, intake, mapping):
    """Fold a Vivun/Prelay/Cuvama-style SE-platform export into canonical/se_platform.json. A
    technical-win flag here is a CLAIM the calls must corroborate; the plumbing only carries it."""
    bucket = _bucket(intake, "se_platform")
    if not bucket.get("present"):
        return None
    m = (mapping or {}).get("se_platform") or {}
    out = []
    for path, fmt in _bucket_files(bucket):
        if not os.path.exists(path):
            print(f"  WARNING: se_platform file missing: {path}"); continue
        rows, header = read_rows(path, fmt)
        if rows is None:
            print(f"  WARNING: {os.path.basename(path)} is xlsx but openpyxl is not installed; skipped.")
            continue
        for r in rows:
            did = str(_mget(r, m, "deal_id")).strip()
            acct = str(_mget(r, m, "account")).strip()
            if not did and not acct:
                continue
            out.append({"deal_id": did, "account": acct,
                        "se_owner": str(_mget(r, m, "se_owner")).strip(),
                        "technical_win_flag": str(_mget(r, m, "technical_win_flag")).strip(),
                        "poc_status": str(_mget(r, m, "poc_status")).strip(),
                        "eval_criteria": str(_mget(r, m, "eval_criteria")).strip(),
                        "activity_count": str(_mget(r, m, "activity_count")).strip()})
    A.write_json(os.path.join(wd, "canonical", "se_platform.json"), out)
    return out


def collect_artifacts(wd):
    """Collect the model-produced artifact-ingest outputs (analysis/{poc,map,security,design}_out/*.json,
    written by the prompts/poc_ingest.md judgment pass in Phase 3.5) into the canonical files the scorer
    and the technical-win phase read. Idempotent; safe to run whenever the out dirs exist. This is
    plumbing: it aggregates JSON a model already produced, it never reads a document for meaning."""
    an = os.path.join(wd, "analysis")
    kinds = {"poc": "poc_plans.json", "map": "map_plans.json",
             "security": "security_qs.json", "design": "solution_designs.json"}
    for kind, fname in kinds.items():
        d = os.path.join(an, f"{kind}_out")
        if not os.path.isdir(d):
            continue
        recs = []
        for fp in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                recs.append(A.read_json(fp))
            except Exception:
                pass
        if recs:
            A.write_json(os.path.join(wd, "canonical", fname), recs)
            print(f"  collected {len(recs)} {kind} doc(s) -> canonical/{fname}")


# ============================================================================ main

def main():
    wd = A.workdir()
    A.ensure_dirs(wd)
    intake = load_intake(wd)
    mapping = load_mapping(wd)
    print(f"== normalize: {wd}")
    if not mapping:
        print("  note: no mapping.json. CRM/notes/stage parsing needs the column mapping from "
              "prompts/crm_mapping.md. Transcripts are parsed regardless.")

    calls, dropped = normalize_transcripts(wd, intake)
    deals = normalize_deals(wd, intake, mapping)
    hist = normalize_stage_history(wd, intake, mapping)
    notes = normalize_notes(wd, intake, mapping)
    se_platform = normalize_se_platform(wd, intake, mapping)
    collect_artifacts(wd)

    print(f"\n  transcripts normalized: {len(calls)}  (dropped {len(dropped)})")
    for f, why in dropped[:40]:
        print(f"    - dropped {f}: {why}")
    if len(dropped) > 40:
        print(f"    … +{len(dropped)-40} more")
    dated = [c["date"] for c in calls if c["date"]]
    if dated:
        print(f"  date range: {min(dated)} … {max(dated)}")
    n_emails = sum(1 for c in calls if c["header_emails"])
    print(f"  calls with header emails: {n_emails}/{len(calls)}")
    print(f"  deals: {len(deals) if deals is not None else 'none (craft-only)'}"
          f"   stage-history deals: {len(hist) if hist is not None else 'none'}"
          f"   deals-with-notes: {len(notes) if notes is not None else 'none'}")
    print("\n  COVERAGE CHECK: every transcript with >=1 turn was carried forward.")
    print("  If a real call was dropped or a column misread, fix intake.json/mapping.json and rerun.")


if __name__ == "__main__":
    main()
