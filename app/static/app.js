const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = u => /^https?:\/\//i.test(u) ? esc(u) : "#";
let opps = [], tasks = [], picked = new Set();

function toast(msg, kind = "good") {
  const d = document.createElement("div"); d.className = "t " + kind; d.textContent = msg;
  $("#toast").append(d); setTimeout(() => d.remove(), 5000);
}
async function api(path, opt = {}) {
  const r = await fetch("/api" + path, {headers: {"Content-Type": "application/json"}, ...opt,
    body: opt.body ? JSON.stringify(opt.body) : undefined});
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {} throw new Error(m); }
  return r.json();
}
const guard = fn => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, "err"); } };

function show(v) {
  document.querySelectorAll(".view").forEach(x => x.hidden = x.id !== "v-" + v);
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.view === v));
  ({dashboard: loadDash, opps: loadOpps, tasks: loadTasks, profile: loadProfile, status: loadStatus}[v] || (() => {}))();
}
$("#nav").onclick = e => e.target.dataset.view && show(e.target.dataset.view);
$("#themeBtn").onclick = () => { const h = document.documentElement; h.dataset.theme = h.dataset.theme === "dark" ? "light" : "dark"; localStorage.setItem("theme", h.dataset.theme); };
document.documentElement.dataset.theme = localStorage.getItem("theme") || "dark";

async function badge() {
  const s = await api("/status"); const b = $("#modeBadge");
  const live = [s.live_ai && "LIVE AI", s.live_search && "LIVE SEARCH"].filter(Boolean);
  b.textContent = live.length ? live.join(" + ") + (s.demo ? " + DEMO" : "") : "DEMO MODE";
  b.className = "badge " + (live.length ? "live" : "demo"); return s;
}

async function loadDash() {
  const [s, runs] = await Promise.all([api("/summary"), api("/runs"), badge()]);
  const stat = (n, l) => `<div class="card stat"><b>${n}</b><span>${l}</span></div>`;
  $("#stats").innerHTML = stat(s.opportunities, "Opportunities") + stat(s.saved, "Saved") + stat(s.tasks_pending, "Tasks pending") + stat(s.tasks_done, "Tasks done") + stat(s.overdue, "Overdue");
  $("#week").innerHTML = s.week.map(t => `<div>${esc(t.title)} <span class="mut">${esc(t.due)}</span></div>`).join("") || `<p class="mut">Nothing due this week. Add a task or run research.</p>`;
  $("#deadlines").innerHTML = s.deadlines.map(d => `<div>${esc(d.title)} <span class="tag">${esc(d.deadline)}</span></div>`).join("") || `<p class="mut">No confirmed deadlines yet. Confirm dates on an opportunity from its source page.</p>`;
  $("#runs").innerHTML = runs.map(r => `<div>${esc(r.at)} ${r.ok ? '<span class="tag ok">ok</span>' : '<span class="tag bad">failed stage</span>'} <span class="mut">${esc(r.query.slice(0, 60))}</span></div>`).join("") || `<p class="mut">No research runs yet.</p>`;
  $("#activity").innerHTML = s.activity.map(a => `<div><span class="mut">${esc(a.at)}</span> ${esc(a.message)}</div>`).join("") || `<p class="mut">Activity appears here.</p>`;
}
$("#qaResearch").onclick = () => show("research");
$("#qaTask").onclick = () => show("tasks");
$("#qaSample").onclick = guard(async () => { const r = await api("/sample", {method: "POST"}); toast(`Loaded ${r.added} DEMO records`); loadDash(); });

$("#rForm").onsubmit = guard(async e => {
  e.preventDefault(); const btn = $("#rBtn"); btn.disabled = true; btn.textContent = "Researching...";
  $("#stages").innerHTML = `<p class="mut">Running 6-stage workflow. This can take a minute with live AI.</p>`;
  try {
    const r = await api("/research", {method: "POST", body: Object.fromEntries(new FormData(e.target))});
    $("#stages").innerHTML = `<div class="card"><h2>Workflow trace</h2>` + r.stages.map(s => `<div class="stage"><b>${esc(s.stage)}</b><span class="${esc(s.status)}">${esc(s.status)}</span><span>${esc(s.detail)}</span></div>`).join("") +
      (r.ok ? `<p>${r.new} new results. <a href="#" id="goOpps">Review opportunities</a></p>` : `<p class="over">A stage failed. Fix the issue (see Connections), then press Run research again. Saved data was kept.</p>`) + `</div>`;
    const g = $("#goOpps"); if (g) g.onclick = ev => { ev.preventDefault(); show("opps"); };
    toast(r.ok ? "Research complete" : "Research stopped at a failed stage", r.ok ? "good" : "err"); badge();
  } finally { btn.disabled = false; btn.textContent = "Run research"; }
});

const dTag = o => ({expired: '<span class="tag bad">deadline expired</span>', unconfirmed: '<span class="tag warn">deadline unconfirmed</span>', upcoming: `<span class="tag ok">closes ${esc(o.deadline)}</span>`})[o.deadline_status];
async function loadOpps() {
  opps = await api("/opportunities"); const f = $("#oFilter").value;
  const list = opps.filter(o => f === "active" ? o.status !== "dismissed" : o.status === f);
  $("#oList").innerHTML = list.map(o => `<div class="card opp"><span class="score" title="Heuristic estimate, not a verified fact">${o.score}/100</span>
    <h3>${esc(o.title)}</h3><div>${o.is_demo ? '<span class="tag warn">DEMO DATA - illustrative, not a real opportunity</span>' : ""}${o.verified ? '<span class="tag ok">deadline verified by you</span>' : '<span class="tag warn">needs confirmation</span>'}${dTag(o)}<span class="tag">${esc(o.kind)}</span><span class="tag">researched ${esc(o.researched_at)}</span></div>
    <p>${esc(o.snippet)}</p><div class="mut">Source: <a href="${safeUrl(o.url)}" target="_blank" rel="noopener noreferrer">${esc(o.url)}</a></div>
    <details><summary>Why this score</summary><div class="bar">${Object.entries(o.breakdown).map(([k, v]) => `<span class="tag">${esc(k.replace(/_/g, " "))}: ${v}</span>`).join("")}</div><pre>${esc(o.analysis || "No AI analysis yet.")}</pre></details>
    <div class="row"><label style="flex-direction:row;align-items:center"><input type="checkbox" style="width:auto" data-cmp="${o.id}" ${picked.has(o.id) ? "checked" : ""}> compare</label>
    <button data-act="saved" data-id="${o.id}">Save</button><button class="ghost" data-act="dismissed" data-id="${o.id}">Dismiss</button>
    <button class="ghost" data-kit="${o.id}">Generate kit</button><button class="ghost" data-dl="${o.id}">Set deadline</button><a class="btn ghost" href="/api/export/pack/${o.id}.md">Export pack</a><button class="ghost danger" data-del="${o.id}">Delete</button></div></div>`).join("")
    || `<div class="card"><p>No opportunities here yet.</p><button onclick="show('research')">Run research</button> <button class="ghost" onclick="$('#qaSample').click()">Load sample workspace</button></div>`;
  loadDocs();
}
$("#oFilter").onchange = guard(loadOpps);
$("#oList").onclick = guard(async e => {
  const d = e.target.dataset;
  if (d.act) { await api(`/opportunities/${d.id}/status`, {method: "PATCH", body: {status: d.act}}); toast("Updated"); loadOpps(); }
  if (d.kit) { e.target.disabled = true; e.target.textContent = "Generating..."; try { const r = await api(`/opportunities/${d.kit}/kit`, {method: "POST"}); toast(`Kit ready (${r.mode}). Review before use.`); } finally { loadOpps(); } }
  if (d.dl) { const v = prompt("Deadline from the official source (YYYY-MM-DD), blank to clear:"); if (v === null) return;
    await api(`/opportunities/${d.dl}/deadline`, {method: "PATCH", body: {deadline: v.trim(), verified: !!v.trim()}}); loadOpps(); }
  if (d.del && confirm("Delete this opportunity and its documents?")) { await api(`/opportunities/${d.del}`, {method: "DELETE"}); loadOpps(); }
  if (d.cmp) { e.target.checked ? picked.add(+d.cmp) : picked.delete(+d.cmp); }
});
$("#cmpBtn").onclick = guard(async () => {
  if (picked.size < 2) return toast("Tick at least two opportunities to compare", "err");
  const rows = await api("/compare?ids=" + [...picked].join(","));
  $("#cmp").innerHTML = `<div class="card"><table><tr><th></th>${rows.map(r => `<th>${esc(r.title)}</th>`).join("")}</tr>` +
    [["Score", r => r.score], ["Type", r => r.kind], ["Deadline", r => r.deadline || "unconfirmed"], ["Verified", r => r.verified ? "yes" : "no"], ["Demo", r => r.is_demo ? "DEMO" : "live"]]
      .map(([l, f]) => `<tr><td>${l}</td>${rows.map(r => `<td>${esc(f(r))}</td>`).join("")}</tr>`).join("") + `</table></div>`;
});
async function loadDocs() {
  const docs = await api("/documents");
  $("#docs").innerHTML = docs.map(d => `<div class="card"><b>${esc(d.title)}</b> <span class="tag ${d.mode === "live-ai" ? "ok" : "warn"}">${d.mode === "live-ai" ? "AI draft - review" : "template (demo)"}</span>
    <textarea id="doc${d.id}" style="min-height:200px">${esc(d.content)}</textarea><div class="row"><button data-save="${d.id}">Save edits</button>
    <button class="ghost" data-copy="${d.id}">Copy</button><a class="btn ghost" href="/api/documents/${d.id}/download?fmt=md">Download .md</a><a class="btn ghost" href="/api/documents/${d.id}/download?fmt=txt">Download .txt</a></div></div>`).join("") || `<p class="mut">Generate a kit from an opportunity to see drafts here.</p>`;
}
$("#docs").onclick = guard(async e => {
  const d = e.target.dataset;
  if (d.save) { await api(`/documents/${d.save}`, {method: "PUT", body: {content: $("#doc" + d.save).value}}); toast("Saved"); }
  if (d.copy) { await navigator.clipboard.writeText($("#doc" + d.copy).value); toast("Copied"); }
});

async function loadTasks() {
  [tasks, opps] = await Promise.all([api("/tasks"), api("/opportunities")]);
  $("#tOpp").innerHTML = `<option value="">None</option>` + opps.map(o => `<option value="${o.id}">${esc(o.title.slice(0, 50))}</option>`).join("");
  const f = $("#tFilter").value, today = new Date().toISOString().slice(0, 10), wk = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
  const list = tasks.filter(t => f === "all" || t.status === f || (f === "overdue" && t.overdue) || (f === "week" && t.status !== "done" && t.due >= today && t.due <= wk));
  $("#tList").innerHTML = list.map(t => `<div class="card"><b>${esc(t.title)}</b> <span class="tag">${esc(t.priority)}</span><span class="tag">${esc(t.status)}</span>
    ${t.due ? `<span class="${t.overdue ? "over" : "mut"}">${t.overdue ? "OVERDUE " : ""}${esc(t.due)}</span>` : ""}
    <div class="row"><button class="ghost" data-done="${t.id}">${t.status === "done" ? "Reopen" : "Mark done"}</button><button class="ghost" data-edit="${t.id}">Edit</button><button class="ghost danger" data-rm="${t.id}">Delete</button></div></div>`).join("")
    || `<div class="card"><p>No tasks match. Add one above.</p></div>`;
}
const taskBody = t => ({title: t.title, opportunity_id: t.opportunity_id, priority: t.priority, due: t.due || "", status: t.status});
$("#tFilter").onchange = guard(loadTasks);
$("#tForm").onsubmit = guard(async e => {
  e.preventDefault(); const f = Object.fromEntries(new FormData(e.target)); const id = f.id; delete f.id;
  f.opportunity_id = f.opportunity_id ? +f.opportunity_id : null;
  await api(id ? `/tasks/${id}` : "/tasks", {method: id ? "PUT" : "POST", body: f});
  e.target.reset(); e.target.id.value = ""; $("#tBtn").textContent = "Add task"; toast("Task saved"); loadTasks();
});
$("#tList").onclick = guard(async e => {
  const d = e.target.dataset, t = tasks.find(x => x.id == (d.done || d.edit || d.rm));
  if (d.done) { await api(`/tasks/${t.id}`, {method: "PUT", body: {...taskBody(t), status: t.status === "done" ? "todo" : "done"}}); loadTasks(); }
  if (d.rm && confirm("Delete this task?")) { await api(`/tasks/${t.id}`, {method: "DELETE"}); loadTasks(); }
  if (d.edit) { const f = $("#tForm"); f.title.value = t.title; f.opportunity_id.value = t.opportunity_id ?? ""; f.priority.value = t.priority; f.due.value = t.due; f.status.value = t.status; f.id.value = t.id; $("#tBtn").textContent = "Update task"; f.title.focus(); }
});

async function loadProfile() { const p = await api("/profile"); for (const k in p) $("#pForm")[k].value = p[k]; }
$("#pForm").onsubmit = guard(async e => { e.preventDefault(); await api("/profile", {method: "PUT", body: Object.fromEntries(new FormData(e.target))}); toast("Profile saved"); });
$("#clrBtn").onclick = guard(async () => { await api("/clear", {method: "POST", body: {confirm: $("#clrTxt").value}}); $("#clrTxt").value = ""; toast("All data cleared"); });

async function loadStatus() { renderStatus(await api("/status")); }
function renderStatus(s) {
  const row = (n, cfg, ok, err, extra) => `<tr><td>${n}</td><td>${cfg ? "key configured" : "no key"}</td><td>${ok ? `<span class="tag ok">LIVE (last ok ${esc(ok)})</span>` : '<span class="tag warn">not yet confirmed</span>'}</td><td>${esc(err || extra || "")}</td></tr>`;
  $("#statusBox").innerHTML = `<table><tr><th>Service</th><th>Config</th><th>State</th><th>Notes</th></tr>${row("Nebius Token Factory (AI)", s.ai_configured, s.ai_last_ok, s.ai_error, s.model + " @ " + s.base_url)}${row("Tavily web search", s.search_configured, s.search_last_ok, s.search_error, "")}</table>
  <p class="note">Mode: ${s.demo ? "DEMO MODE active for anything not yet confirmed live." : "Both integrations confirmed live."}</p>`;
}
$("#checkBtn").onclick = guard(async () => { const b = $("#checkBtn"); b.disabled = true; try { const r = await api("/status/check", {method: "POST"}); renderStatus(r); toast(`AI: ${r.ai === "ok" ? "ok" : "failed"}; Search: ${r.search === "ok" ? "ok" : "failed"}`, r.ai === "ok" && r.search === "ok" ? "good" : "err"); badge(); } finally { b.disabled = false; } });

badge().then(() => { if (!localStorage.getItem("seen")) { toast("Welcome! Load the sample workspace to explore, or run research."); localStorage.setItem("seen", "1"); } }); loadDash().catch(() => {});
