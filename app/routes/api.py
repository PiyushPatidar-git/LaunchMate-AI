import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models as m, schemas as s
from ..config import settings
from ..services import ai, search, core, workflow

router = APIRouter(prefix="/api")

def opp_dict(o):
    return {"id": o.id, "title": o.title, "url": o.url, "kind": o.kind, "snippet": o.snippet, "published": o.published,
            "deadline": o.deadline, "deadline_status": core.deadline_status(o.deadline), "score": o.score,
            "breakdown": json.loads(o.breakdown or "{}"), "analysis": o.analysis, "verified": o.verified,
            "is_demo": o.is_demo, "status": o.status, "researched_at": o.researched_at.date().isoformat()}

def task_dict(t):
    return {"id": t.id, "title": t.title, "opportunity_id": t.opportunity_id, "priority": t.priority, "due": t.due,
            "status": t.status, "overdue": bool(t.due and t.status != "done" and t.due < date.today().isoformat())}

def get_opp(db, oid):
    o = db.get(m.Opportunity, oid)
    if not o: raise HTTPException(404, "Opportunity not found")
    return o

def profile(db):
    p = db.scalar(select(m.Profile))
    if not p:
        p = m.Profile(); db.add(p); db.commit()
    return p

@router.get("/health")
def health(): return {"status": "ok"}

def mode_info():
    return {"live_ai": bool(ai.state["live_ok_at"]), "live_search": bool(search.state["live_ok_at"]),
            "demo": not (ai.state["live_ok_at"] and search.state["live_ok_at"]),
            "ai_configured": ai.configured(), "search_configured": search.configured(),
            "model": settings.model, "base_url": settings.nebius_url,
            "ai_last_ok": ai.state["live_ok_at"], "search_last_ok": search.state["live_ok_at"],
            "ai_error": ai.state["last_error"], "search_error": search.state["last_error"]}

@router.get("/status")
def status(): return mode_info()

@router.post("/status/check")
def check():
    """Real connectivity checks; a flag turns LIVE only after an actual successful response."""
    out = {}
    try: ai.chat("Reply with the single word: ok", "ping", max_tokens=20); out["ai"] = "ok"
    except ai.AIUnavailable as e: out["ai"] = str(e)
    try: search.search("hackathon", 1); out["search"] = "ok"
    except search.SearchUnavailable as e: out["search"] = str(e)
    return {**out, **mode_info()}

@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    p = profile(db)
    return {k: getattr(p, k) for k in ("nickname", "skills", "interests", "goals", "experience")}

@router.put("/profile")
def put_profile(body: s.ProfileIn, db: Session = Depends(get_db)):
    p = profile(db)
    for k, v in body.model_dump().items(): setattr(p, k, v)
    db.commit(); return {"ok": True}

@router.post("/research")
def research(body: s.ResearchIn, db: Session = Depends(get_db)):
    return workflow.run_research(db, body)

@router.get("/runs")
def runs(db: Session = Depends(get_db)):
    return [{"id": r.id, "at": r.at.isoformat(timespec="minutes"), "query": r.query, "ok": r.ok, "stages": json.loads(r.stages)}
            for r in db.scalars(select(m.Run).order_by(m.Run.id.desc()).limit(10))]

@router.get("/opportunities")
def list_opps(db: Session = Depends(get_db)):
    return [opp_dict(o) for o in db.scalars(select(m.Opportunity).order_by(m.Opportunity.score.desc()))]

@router.patch("/opportunities/{oid}/status")
def set_status(oid: int, body: s.StatusIn, db: Session = Depends(get_db)):
    o = get_opp(db, oid); o.status = body.status; db.commit()
    workflow.log(db, "opportunity", f"{body.status}: {o.title[:80]}"); return opp_dict(o)

@router.patch("/opportunities/{oid}/deadline")
def set_deadline(oid: int, body: s.DeadlineIn, db: Session = Depends(get_db)):
    o = get_opp(db, oid); o.deadline = body.deadline; o.verified = body.verified and bool(body.deadline); db.commit()
    return opp_dict(o)

@router.delete("/opportunities/{oid}")
def del_opp(oid: int, db: Session = Depends(get_db)):
    o = get_opp(db, oid); db.execute(delete(m.Document).where(m.Document.opportunity_id == oid)); db.delete(o); db.commit()
    return {"ok": True}

@router.get("/compare")
def compare(ids: str, db: Session = Depends(get_db)):
    try: idl = [int(i) for i in ids.split(",") if i]
    except ValueError: raise HTTPException(422, "ids must be integers")
    return [opp_dict(get_opp(db, i)) for i in idl]

@router.post("/opportunities/{oid}/kit")
def kit(oid: int, db: Session = Depends(get_db)):
    o = get_opp(db, oid)
    try: text, mode = workflow.generate_kit(db, o, profile(db))
    except ai.AIUnavailable as e: raise HTTPException(502, str(e))
    d = m.Document(opportunity_id=oid, title=f"Application kit - {o.title[:80]}", content=text, mode=mode)
    db.add(d); db.commit(); workflow.log(db, "kit", f"Kit generated ({mode}) for {o.title[:60]}")
    return {"id": d.id, "mode": mode}

@router.get("/documents")
def docs(opportunity_id: int | None = None, db: Session = Depends(get_db)):
    q = select(m.Document).order_by(m.Document.id.desc())
    if opportunity_id: q = q.where(m.Document.opportunity_id == opportunity_id)
    return [{"id": d.id, "opportunity_id": d.opportunity_id, "title": d.title, "content": d.content, "mode": d.mode} for d in db.scalars(q)]

@router.put("/documents/{did}")
def edit_doc(did: int, body: s.DocIn, db: Session = Depends(get_db)):
    d = db.get(m.Document, did)
    if not d: raise HTTPException(404, "Document not found")
    d.content = body.content; db.commit(); return {"ok": True}

@router.get("/documents/{did}/download")
def dl_doc(did: int, fmt: str = "md", db: Session = Depends(get_db)):
    d = db.get(m.Document, did)
    if not d: raise HTTPException(404, "Document not found")
    ext = "txt" if fmt == "txt" else "md"
    return Response(d.content, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="kit-{did}.{ext}"'})

@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return [task_dict(t) for t in db.scalars(select(m.Task).order_by(m.Task.due == "", m.Task.due))]

@router.post("/tasks")
def add_task(body: s.TaskIn, db: Session = Depends(get_db)):
    if body.opportunity_id: get_opp(db, body.opportunity_id)
    t = m.Task(**body.model_dump()); db.add(t); db.commit(); return task_dict(t)

@router.put("/tasks/{tid}")
def edit_task(tid: int, body: s.TaskIn, db: Session = Depends(get_db)):
    t = db.get(m.Task, tid)
    if not t: raise HTTPException(404, "Task not found")
    for k, v in body.model_dump().items(): setattr(t, k, v)
    db.commit(); return task_dict(t)

@router.delete("/tasks/{tid}")
def del_task(tid: int, db: Session = Depends(get_db)):
    t = db.get(m.Task, tid)
    if not t: raise HTTPException(404, "Task not found")
    db.delete(t); db.commit(); return {"ok": True}

@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    opps = list(db.scalars(select(m.Opportunity))); tasks = [task_dict(t) for t in db.scalars(select(m.Task))]
    today = date.today().isoformat(); week = (date.today() + timedelta(days=7)).isoformat()
    return {"opportunities": len([o for o in opps if o.status != "dismissed"]), "saved": len([o for o in opps if o.status == "saved"]),
            "deadlines": sorted([{"title": o.title, "deadline": o.deadline} for o in opps if o.deadline and o.deadline >= today and o.status != "dismissed"], key=lambda x: x["deadline"])[:5],
            "tasks_done": len([t for t in tasks if t["status"] == "done"]), "tasks_pending": len([t for t in tasks if t["status"] != "done"]),
            "overdue": len([t for t in tasks if t["overdue"]]),
            "week": [t for t in tasks if t["status"] != "done" and today <= t["due"] <= week],
            "activity": [{"at": a.at.isoformat(timespec="minutes"), "message": a.message} for a in db.scalars(select(m.Activity).order_by(m.Activity.id.desc()).limit(8))]}

@router.post("/sample")
def sample(db: Session = Depends(get_db)):
    new = 0
    for r in search.DEMO:
        n = core.normalize_url(r["url"])
        if db.scalar(select(m.Opportunity).where(m.Opportunity.url_norm == n)): continue
        sc, parts = core.score_fit(r["title"] + r["snippet"], "python ai", "python fastapi", "", "hackathon")
        db.add(m.Opportunity(title=r["title"], url=r["url"], url_norm=n, snippet=r["snippet"], score=sc,
                             breakdown=json.dumps(parts), analysis="DEMO DATA: not analysed by AI.", is_demo=True, status="saved")); new += 1
    db.commit(); workflow.log(db, "sample", f"Sample workspace loaded ({new} DEMO records)"); return {"added": new}

@router.get("/export/{what}.csv")
def export_csv(what: str, db: Session = Depends(get_db)):
    if what == "opportunities":
        rows = [opp_dict(o) for o in db.scalars(select(m.Opportunity))]
        f = ["id", "title", "url", "kind", "status", "score", "deadline", "deadline_status", "verified", "is_demo", "researched_at"]
    elif what == "tasks":
        rows = [task_dict(t) for t in db.scalars(select(m.Task))]; f = ["id", "title", "opportunity_id", "priority", "due", "status"]
    else: raise HTTPException(404, "Unknown export")
    return Response(core.csv_text(rows, f), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{what}.csv"'})

@router.get("/export/pack/{oid}.md")
def export_pack(oid: int, db: Session = Depends(get_db)):
    o = get_opp(db, oid)
    docs_ = [{"title": d.title, "content": d.content} for d in db.scalars(select(m.Document).where(m.Document.opportunity_id == oid))]
    tasks_ = [task_dict(t) for t in db.scalars(select(m.Task).where(m.Task.opportunity_id == oid))]
    return Response(core.markdown_pack(opp_dict(o), docs_, tasks_), media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="pack-{oid}.md"'})

@router.post("/clear")
def clear(body: s.ClearIn, db: Session = Depends(get_db)):
    if body.confirm != "DELETE": raise HTTPException(400, "Type DELETE to confirm.")
    for model in (m.Document, m.Task, m.Opportunity, m.Run, m.Activity, m.Profile): db.execute(delete(model))
    db.commit(); return {"ok": True}
