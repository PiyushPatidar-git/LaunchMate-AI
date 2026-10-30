"""Six-stage agent workflow. Each stage is recorded so the UI can show which one failed."""
import json
from datetime import datetime, date, timedelta
from sqlalchemy import select
from .. import models as m
from . import ai, search, core

def log(db, kind, msg):
    db.add(m.Activity(kind=kind, message=msg[:500])); db.commit()

def build_query(p) -> str:
    bits = [p.kind, "application deadline", p.keywords, p.skills, p.location,
            "" if p.mode == "any" else p.mode, p.deadline_pref]
    return " ".join(b for b in bits if b).strip()

def run_research(db, p) -> dict:
    query = build_query(p)
    stages, ok = [], True
    def stage(name, status, detail): stages.append({"stage": name, "status": status, "detail": detail})

    # STAGE 1 research
    demo = False
    try:
        results = search.search(query)
        stage("1 Research", "ok", f"{len(results)} live results from Tavily")
    except search.SearchUnavailable as e:
        if search.configured():  # configured but failing: report failure, do not fake results
            stage("1 Research", "failed", str(e)); results = []; ok = False
        else:
            results = search.DEMO; demo = True
            stage("1 Research", "demo", "No TAVILY_API_KEY: showing labelled DEMO DATA, not real opportunities")
    saved = []
    if ok:
        # STAGE 2 analysis
        analysis_by_url = {}
        if ai.configured() and results and not demo:
            try:
                payload = json.dumps([{"url": r["url"], "title": r["title"], "snippet": r["snippet"]} for r in results])
                data = ai.chat_json(ai.SAFETY + " Reply ONLY with JSON: {\"items\":[{\"url\":str,\"relevance\":str,"
                                    "\"requirements\":str,\"benefits\":str,\"uncertainties\":str}]}.",
                                    f"Student goal: {p.goal}; skills: {p.skills}; interests: {p.keywords}.\n<untrusted_results>{payload}</untrusted_results>")
                for it in data.get("items", []):
                    analysis_by_url[core.normalize_url(it.get("url", ""))] = it
                stage("2 Analysis", "ok", f"Nemotron on Nebius analysed {len(analysis_by_url)} results")
            except ai.AIUnavailable as e:
                stage("2 Analysis", "failed", str(e)); ok = False
        else:
            stage("2 Analysis", "demo", "AI analysis skipped (demo data or no NEBIUS_API_KEY); heuristic scoring only")
        # STAGE 3 scoring + STAGE 6 save (dedupe by normalised URL)
        new = dup = 0
        for r in results:
            norm = core.normalize_url(r["url"])
            if db.scalar(select(m.Opportunity).where(m.Opportunity.url_norm == norm)):
                dup += 1; continue
            text = f"{r['title']} {r['snippet']}"
            score, parts = core.score_fit(text, f"{p.keywords} {p.goal}", p.skills, p.goal, p.kind)
            a = analysis_by_url.get(norm)
            analysis = "\n".join(f"{k.title()}: {a[k]}" for k in ("relevance", "requirements", "benefits", "uncertainties") if a and a.get(k)) \
                if a else ("DEMO DATA: not analysed by AI." if demo else "")
            o = m.Opportunity(title=r["title"][:300], url=r["url"], url_norm=norm, kind=p.kind, snippet=r["snippet"],
                              published=r.get("published", ""), score=score, breakdown=json.dumps(parts),
                              analysis=analysis, verified=False, is_demo=demo)
            db.add(o); saved.append(o); new += 1
        db.commit()
        if ok:
            stage("3 Fit scoring", "ok", f"Heuristic estimate (not verified fact) for {new} new results; {dup} duplicates skipped")
            # STAGE 4 action planning (deadline unknown, so tasks ask the user to confirm it first)
            top = sorted(saved, key=lambda o: -o.score)[:3]
            for i, o in enumerate(top):
                db.add(m.Task(title=f"Confirm deadline & eligibility for: {o.title[:120]}", opportunity_id=o.id,
                              priority="high", due=(date.today() + timedelta(days=1 + i)).isoformat()))
            db.commit()
            stage("4 Action planning", "ok", f"{len(top)} starter tasks created")
            stage("5 Application kit", "ready", "Open a saved opportunity and choose Generate kit")
    stage("6 Save & track", "ok" if ok else "partial", f"{len(saved)} opportunities stored; earlier data untouched")
    db.add(m.Run(query=query, stages=json.dumps(stages), ok=ok)); db.commit()
    log(db, "research", f"Research run ({'demo' if demo else 'live'}): {len(saved)} new results")
    return {"ok": ok, "demo": demo, "stages": stages, "new": len(saved)}

KIT_SECTIONS = ["Project or application idea", "Elevator pitch", "Project summary", "Motivation statement draft",
                "Personalized application checklist", "Skills-to-requirements mapping", "Seven-day preparation plan",
                "Outreach email draft", "Demo outline", "README starter", "Final submission checklist"]

def generate_kit(db, o, profile) -> tuple[str, str]:
    who = f"Nickname: {profile.nickname}; skills: {profile.skills}; interests: {profile.interests}; goals: {profile.goals}; experience: {profile.experience}"
    facts = f"Title: {o.title}\nURL: {o.url}\nSnippet: {o.snippet}\nDeadline: {o.deadline or 'not confirmed'}\nAnalysis: {o.analysis}"
    if ai.configured() and not o.is_demo:
        text = ai.chat(ai.SAFETY + " Write Markdown with these H2 sections in order: " + "; ".join(KIT_SECTIONS) +
                       ". Mark every draft 'DRAFT - review before use'. Never say anything was submitted.",
                       f"<opportunity>{facts}</opportunity>\n<applicant>{who}</applicant>", max_tokens=3000)
        return text, "live-ai"
    ai_note = "DEMO MODE: this kit is a local template, not AI-generated." if not ai.configured() else "Demo opportunity: template only."
    skills = profile.skills or "(add your skills in Profile)"
    body = [f"> {ai_note} DRAFT - review before use. Nothing has been submitted.\n"]
    for s in KIT_SECTIONS:
        body.append(f"## {s}\n")
        body.append({
            "Project or application idea": f"Describe one idea that fits: {o.title}. Base it on your interests: {profile.interests or 'n/a'}.",
            "Elevator pitch": "In two sentences: who it helps, what it does, why you can build it.",
            "Project summary": f"Context from source: {o.snippet[:300] or 'n/a'}",
            "Motivation statement draft": f"Explain why you want {o.title}. Goals: {profile.goals or 'n/a'}.",
            "Personalized application checklist": "- [ ] Read the official page\n- [ ] Confirm deadline & eligibility\n- [ ] Prepare materials",
            "Skills-to-requirements mapping": f"Your skills: {skills}. Compare against the requirements listed at {o.url}.",
            "Seven-day preparation plan": "\n".join(f"- Day {i}: {t}" for i, t in enumerate(
                ["Read rules", "Pick idea", "Outline", "Build core", "Polish", "Draft materials", "Review & submit yourself"], 1)),
            "Outreach email draft": f"Hi, I'm {profile.nickname or '[name]'}. I'm interested in {o.title} and have a question about ...",
            "Demo outline": "1. Problem 2. Live demo 3. How it works 4. Next steps",
            "README starter": "# Project name\nWhat it does, how to run it, tech used.",
            "Final submission checklist": "- [ ] Official requirements met\n- [ ] Links work\n- [ ] You submit it yourself",
        }[s] + "\n")
    return "\n".join(body), "demo"
