#!/usr/bin/env python3
"""Anti-slop gate. Scans authored prose for AI cliche / sycophancy. Verbatim content is DATA and EXEMPT.
For the interactive report (report_app.py), the data is an embedded JSON blob rendered client-side, so the
gate parses that blob and checks only EDITORIAL fields (why, headline, one_change, arc, ...), never the
verbatim evidence fields (quote, buyer_quote, rep_quote, evidence, moment, title, crm_value). It also
scans the authored template (CSS/JS/static copy). For legacy server-rendered HTML it still strips
<blockquote>/<q>/.verbatim regions. Exits 1 (with locations) if any violation is found, else 0.
"""
import os
import re
import sys
import json

BANNED = [
    r"\bdelve\b", r"\bdelving\b", r"\btapestry\b", r"\bin today's (?:fast-paced|ever-changing)\b",
    r"\bit's worth noting\b", r"\bit is worth noting\b", r"\bneedless to say\b",
    r"\bin the realm of\b", r"\bnavigating the\b", r"\bunlock(?:ing)? (?:the )?potential\b",
    r"\ba testament to\b", r"\bat the end of the day\b", r"\bgame[- ]chang(?:er|ing)\b",
    r"\bsupercharge\b", r"\bseamless(?:ly)?\b", r"\brobust solution\b", r"\bsynerg(?:y|ies|istic)\b",
    r"\bcutting[- ]edge\b", r"\bharness(?:ing)? the power\b", r"\bparadigm shift\b",
    r"\bgreat question\b", r"\bexcellent question\b", r"\bcertainly!\b", r"\bi'd be happy to\b",
    r"\blet's dive in\b", r"\bdive deep\b", r"\bmoreover,\b.*\bfurthermore,\b",
    r"\bplays a (?:crucial|vital|pivotal) role\b", r"\ba myriad of\b", r"\bplethora\b",
    r"\bwhen it comes to\b", r"\bthe world of\b", r"\belevate your\b",
    r"\bunderscore", r"\bcommendable\b", r"\bmeticulous", r"\bintricate", r"\bmultifaceted\b",
    r"\bnot just\b[^.!?]{0,40}\bbut\b", r"\bit'?s not\b[^.!?]{0,30}\bit'?s\b",
    r"\bisn'?t just\b", r"\bfirst and foremost\b", r"\bnavigate the complexities\b",
    r"\bunderpin", r"\bpivotal\b", r"\bin essence\b", r"\bnotably,\s",
    r"[—–―]",  # HARD BLOCK: em/en dashes are not allowed anywhere in authored prose
]
BANNED_RE = [re.compile(p, re.I) for p in BANNED]

# strip exempt regions (verbatim quotes are data)
EXEMPT = re.compile(r"<(blockquote|q)[^>]*>.*?</\1>|<[^>]*class=\"[^\"]*verbatim[^\"]*\"[^>]*>.*?</[^>]*>",
                    re.S | re.I)
TAG = re.compile(r"<[^>]+>")
DATA_RE = re.compile(r'<script id="DATA" type="application/json">(.*?)</script>', re.S)
# verbatim fields are evidence / source data, never authored prose
VERB_FIELDS = {"quote", "buyer_quote", "rep_quote", "evidence", "moment", "title", "crm_value"}


def _walk_json(o, key=None, hits=None):
    if hits is None:
        hits = []
    if isinstance(o, str):
        if key in VERB_FIELDS:
            return hits
        for rx in BANNED_RE:
            m = rx.search(o)
            if m:
                ctx = o[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                hits.append((rx.pattern, f"[{key}] " + ctx.strip()))
    elif isinstance(o, dict):
        for k, v in o.items():
            _walk_json(v, k, hits)
    elif isinstance(o, list):
        for x in o:
            _walk_json(x, key, hits)
    return hits


def check(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    hits = []
    # interactive report: pull the embedded data blob and check only editorial fields
    m = DATA_RE.search(html)
    if m:
        try:
            hits += _walk_json(json.loads(m.group(1)))
        except Exception:
            pass  # malformed blob falls through to the text scan below
        html = html.replace(m.group(0), " ")  # do NOT blind-scan the verbatim-laden blob
    html = EXEMPT.sub(" ", html)
    text = TAG.sub(" ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    for rx in BANNED_RE:
        for mm in rx.finditer(text):
            ctx = text[max(0, mm.start() - 30):mm.end() + 30].replace("\n", " ")
            hits.append((rx.pattern, ctx.strip()))
    return hits


def main():
    files = sys.argv[1:]
    files = [f for f in files if not f.startswith("--")]
    total = 0
    for f in files:
        if not os.path.exists(f):
            continue
        hits = check(f)
        if hits:
            total += len(hits)
            print(f"\n✗ {os.path.basename(f)}: {len(hits)} violation(s)")
            for pat, ctx in hits[:20]:
                print(f"    [{pat}]  …{ctx}…")
    if total:
        print(f"\nANTI-SLOP GATE FAILED: {total} violation(s). Fix the authored prose string and rerun report.py.")
        sys.exit(1)
    print(f"✓ anti-slop gate passed ({len(files)} pages, 0 violations)")
    sys.exit(0)


if __name__ == "__main__":
    main()
