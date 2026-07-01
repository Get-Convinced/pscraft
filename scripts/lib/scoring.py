"""Small scoring helpers shared by the API-mode driver scripts. Pure functions, no model calls."""


def rubric_anchors(rubric):
    """Render the rubric dimensions + their 1-5 anchors as the block the scorer reads."""
    return "\n".join(f"  {d['id']} - {d['name']} [{d['group']}]: {d['anchors']}" for d in rubric["dimensions"])


def norm_score(s):
    if s in (None, "", "NA", "na", "N/A"):
        return "NA"
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return "NA"


def normalize_rep(r):
    """Coerce a rep's raw scored dims into the canonical {dim: {score, confidence, why, quote}} shape and
    enforce the quote rule: an extreme score (1,2,4,5) with no verbatim quote is down-weighted to low
    confidence rather than trusted at face value."""
    out = dict(r)
    sc = {}
    for dim, cell in (r.get("scores") or {}).items():
        if not isinstance(cell, dict):
            cell = {"score": cell}
        cell["score"] = norm_score(cell.get("score"))
        cell.setdefault("confidence", "medium")
        if cell["score"] in (1, 2, 4, 5) and not str(cell.get("quote", "")).strip():
            cell["confidence"] = "low"
            cell["_unquoted"] = True
        sc[dim] = cell
    out["scores"] = sc
    return out
