from datetime import date
from app.services import core

def test_normalize_url_strips_tracking_and_www():
    assert core.normalize_url("HTTPS://www.Example.com/a/?utm_source=x&id=2#frag") == "https://example.com/a?id=2"

def test_deadline_status():
    t = date(2026, 1, 10)
    assert core.deadline_status("", t) == "unconfirmed"
    assert core.deadline_status("2026-01-01", t) == "expired"
    assert core.deadline_status("2026-02-01", t) == "upcoming"
    assert core.deadline_status("garbage", t) == "unconfirmed"

def test_score_is_bounded_and_explained():
    s, parts = core.score_fit("Python AI hackathon for students", "python ai", "python", "agents", "hackathon")
    assert 0 <= s <= 100 and sum(parts.values()) == s
    assert parts["keyword_match"] == 40 and parts["deadline_feasibility"] == 5

def test_csv_blocks_formula_injection():
    out = core.csv_text([{"a": "=SUM(1)", "b": "ok"}], ["a", "b"])
    assert "'=SUM(1)" in out and out.startswith("a,b")

def test_markdown_pack_labels_drafts_and_demo():
    md = core.markdown_pack({"title": "T", "url": "https://x.io", "researched_at": "2026-01-01", "deadline": "", "is_demo": True},
                            [{"title": "Kit", "content": "body"}], [{"status": "done", "title": "x", "due": "", "priority": "high"}])
    assert "UNCONFIRMED" in md and "DEMO DATA" in md and "review" in md and "- [x] x" in md
