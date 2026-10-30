"""Pure helpers (no network, no database): URL normalisation, scoring, exports."""
import csv, io, re
from datetime import date
from urllib.parse import urlsplit, urlunsplit

TRACKING = ("utm_", "ref", "fbclid", "gclid")

def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = "&".join(x for x in p.query.split("&") if x and not x.lower().startswith(TRACKING))
    return urlunsplit((p.scheme.lower() or "https", host, p.path.rstrip("/"), q, ""))

def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]{2,}", (text or "").lower()) if t not in {"and", "the", "for", "with"}}

def deadline_status(deadline: str, today: date | None = None) -> str:
    """'unconfirmed' unless a deadline date was entered; otherwise 'expired'/'upcoming'."""
    if not deadline:
        return "unconfirmed"
    try:
        d = date.fromisoformat(deadline)
    except ValueError:
        return "unconfirmed"
    return "expired" if d < (today or date.today()) else "upcoming"

def score_fit(text: str, keywords: str, skills: str, goal: str, kind: str, deadline: str = "",
              today: date | None = None) -> tuple[float, dict]:
    """Interpretable heuristic 0-100. This is an estimate, NOT a verified fact."""
    t = tokens(text)
    def overlap(src: str) -> float:
        s = tokens(src)
        return len(s & t) / len(s) if s else 0.0
    parts = {
        "keyword_match": round(40 * overlap(keywords)),
        "skill_alignment": round(25 * overlap(skills)),
        "goal_alignment": round(15 * overlap(goal)),
        "type_match": 10 if kind.lower() in text.lower() else 0,
    }
    st = deadline_status(deadline, today)
    parts["deadline_feasibility"] = {"upcoming": 10, "unconfirmed": 5, "expired": 0}[st]
    return float(sum(parts.values())), parts

def csv_text(rows: list[dict], fields: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        # neutralise spreadsheet formula injection
        w.writerow({k: ("'" + str(v) if str(v)[:1] in "=+-@" else v) for k, v in r.items()})
    return buf.getvalue()

def markdown_pack(opp: dict, docs: list[dict], tasks: list[dict]) -> str:
    out = [f"# Preparation pack: {opp['title']}", "", f"Source: {opp['url']}", f"Researched: {opp['researched_at']}",
           f"Deadline: {opp['deadline'] or 'UNCONFIRMED - check the source'}", "",
           "> Drafts below need your review. Nothing has been submitted for you.", ""]
    if opp.get("is_demo"):
        out += ["> DEMO DATA: illustrative sample, not a verified live opportunity.", ""]
    for d in docs:
        out += [f"## {d['title']}", "", d["content"], ""]
    if tasks:
        out += ["## Tasks", ""] + [f"- [{'x' if t['status']=='done' else ' '}] {t['title']} (due {t['due'] or 'n/a'}, {t['priority']})" for t in tasks]
    return "\n".join(out) + "\n"
