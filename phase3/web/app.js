"use strict";

const STARTERS = [
  "How is the business doing?",
  "What should I be concerned about?",
  "Why is profitability falling?",
  "How is Germany performing?",
  "Where should management focus next?",
];
const SYSTEM_COLOR = { ERP: "var(--erp)", CRM: "var(--crm)", Payroll: "var(--payroll)", Mappings: "var(--mappings)", Metadata: "var(--muted)" };
const SYSTEM_PRODUCT = { ERP: "e-conomic", CRM: "HubSpot", Payroll: "Danløn", Mappings: "ID mappings", Metadata: "metadata" };
const TOOL_LABEL = {
  meta_describe_sources: "Reviewing available sources", meta_get_semantics: "Reading data definitions",
  erp_financial_summary: "Profit & loss", erp_sales_summary: "Revenue and margin", erp_customer_revenue: "Revenue by customer",
  erp_operating_costs: "Operating costs", erp_ledger_entries: "Ledger entries", erp_find_customers: "Customer lookup",
  erp_invoices: "Invoices", erp_invoice_lines: "Invoice lines", erp_products: "Product catalogue",
  crm_pipeline: "Sales pipeline", crm_win_rate: "Win rates", crm_loss_reasons: "Loss reasons", crm_deals: "Deals",
  crm_renewals: "Service renewals", crm_find_companies: "Company lookup", crm_activities: "Sales activity notes",
  crm_activity_summary: "Sales activity volume", crm_owner_history: "Account ownership changes", crm_users: "Sales team",
  payroll_headcount: "Headcount", payroll_personnel_costs: "Personnel costs", payroll_base_salary_change: "Salary changes",
  payroll_find_employees: "Employee lookup", payroll_entries: "Pay slips", payroll_hires_and_departures: "Hires and departures",
  identity_crm_companies_to_erp: "Matching CRM companies to ERP customers", identity_erp_customers_to_crm: "Matching ERP customers to CRM",
  identity_crm_users_to_employees: "Matching sales reps to payroll", identity_employees_to_crm_users: "Matching employees to CRM users",
  identity_find_company: "Finding a company across systems", identity_find_person: "Finding a person across systems",
  present_answer: "Preparing the answer",
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
const sysChip = (s, extra = "") => `<span class="sys ${extra}" style="--c:${SYSTEM_COLOR[s] || "var(--muted)"}" title="${esc(SYSTEM_PRODUCT[s] || s)}">${esc(s)}</span>`;
const fmtInt = (n) => (n == null ? "–" : Number(n).toLocaleString("en-US"));
const fmtMonth = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "");

let conversationId = null;
let busy = false;

async function loadConfig() {
  const cfg = await (await fetch("/api/config")).json();
  $("meta").textContent = `Read-only · synthetic company data · ${cfg.agent.model}`;
  $("sources").innerHTML = cfg.sources.map((s) => `
    <div class="source" style="--c:${SYSTEM_COLOR[s.system]}">
      <div class="row"><div class="name">${esc(s.product)}<span class="role">— ${esc(s.role)}</span></div><div class="status">Connected</div></div>
      <div class="stats">${s.stats.map((x) => `${fmtInt(x.count)} ${esc(x.label)}`).join(" · ")}</div>
      <div class="stats">${fmtMonth(s.coverage[0])} – ${fmtMonth(s.coverage[1])}</div>
    </div>`).join("");
}

function renderStarters() {
  $("starters").innerHTML = STARTERS.map((q) => `<button class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("");
}

const store = { get: () => { try { return sessionStorage.getItem("nordflow-conversation"); } catch { return null; } },
  set: (v) => { try { sessionStorage.setItem("nordflow-conversation", v); } catch { /* ignore */ } } };

async function newConversation() {
  conversationId = (await (await fetch("/api/conversations", { method: "POST" })).json()).id;
  store.set(conversationId);
  [...$("thread").querySelectorAll(".turn")].forEach((n) => n.remove());
  $("empty").hidden = false;
}

async function restoreOrStart() {
  const saved = new URLSearchParams(location.search).get("c") || store.get();  // ?c=<id> reopens a conversation
  if (saved) {
    const res = await fetch(`/api/conversations/${saved}`);
    if (res.ok) {
      conversationId = saved;
      const { turns } = await res.json();
      if (turns.length) $("empty").hidden = true;
      for (const t of turns) {
        const el = document.createElement("div");
        el.className = "turn";
        el.innerHTML = `<div class="q"><span>${esc(t.question)}</span></div>${renderAnswer(t)}`;
        $("thread").appendChild(el);
      }
      return;
    }
  }
  await newConversation();
}

function setBusy(v) {
  busy = v;
  $("send").disabled = v; $("input").disabled = v;
  document.querySelectorAll(".chip").forEach((c) => (c.disabled = v));
}

function renderAnswer(turn) {
  const a = turn.answer;
  const dataCalls = turn.tool_calls.filter((c) => c.tool !== "present_answer");
  if (!a) {
    const msg = turn.errors.length ? turn.errors.join(" ") : "No answer was produced.";
    return `<div class="a"><p class="headline error">${esc(msg)}</p>${traceHtml(dataCalls, turn)}</div>`;
  }
  const points = (a.key_points || []).length ? `<ul class="points">${a.key_points.map((p) => `<li>${rich(p)}</li>`).join("")}</ul>` : "";
  const evidence = (a.evidence || []).length ? `
    <div class="label">Evidence</div>
    <table class="evidence"><colgroup><col class="metric"><col><col class="period"><col class="src"></colgroup><tbody>${a.evidence.map((e) => `
      <tr><td>${esc(e.metric)}</td><td class="value">${esc(e.value)}</td><td class="period">${esc(e.period || "")}</td>
      <td>${sysChip(e.system, e.verified_source ? "" : "unverified")}</td></tr>`).join("")}</tbody></table>` : "";
  const sources = turn.sources.length ? `<div class="sourceline">Sources: ${turn.sources.map((s) => sysChip(s)).join("")}</div>` : "";
  const follow = (a.follow_up_questions || []).length ? `
    <div class="followups"><div class="label">Ask next</div><div class="chips">${a.follow_up_questions.map((q) => `<button class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div></div>` : "";
  const warn = turn.errors.length ? `<p class="error">${esc(turn.errors.join(" "))}</p>` : "";
  return `<div class="a"><p class="headline">${rich(a.headline)}</p>${points}${evidence}${sources}${follow}${warn}${traceHtml(dataCalls, turn)}</div>`;
}

function traceHtml(calls, turn) {
  if (!calls.length) return "";
  const systems = [...new Set(calls.map((c) => c.system))].filter((s) => s !== "Metadata");
  return `<details class="trace"><summary>How this was investigated · ${calls.length} data queries across ${systems.join(", ") || "metadata"} · ${turn.elapsed_s}s</summary>
    <ol>${calls.map((c) => `<li>${sysChip(c.system)} ${esc(TOOL_LABEL[c.tool] || c.tool)} <code>${esc(c.tool)} ${esc(JSON.stringify(c.arguments))}</code>
      ${c.ok === false ? `<div class="err">Error: ${esc(c.error)}</div>` : ""}</li>`).join("")}</ol></details>`;
}

async function ask(question) {
  if (busy || !question.trim()) return;
  if (!conversationId) await newConversation();
  $("empty").hidden = true;
  setBusy(true);
  const turnEl = document.createElement("div");
  turnEl.className = "turn";
  turnEl.innerHTML = `<div class="q"><span>${esc(question)}</span></div>
    <div class="progress"><div class="line"><div class="spinner"></div><span class="status-text">Investigating…</span></div><ul></ul></div>`;
  $("thread").appendChild(turnEl);
  turnEl.scrollIntoView({ behavior: "smooth", block: "start" });
  const started = Date.now();
  const calls = new Map();
  const statusText = turnEl.querySelector(".status-text");
  const list = turnEl.querySelector(".progress ul");
  const timer = setInterval(() => {
    const n = [...calls.values()].filter((c) => c.tool !== "present_answer").length;
    statusText.textContent = `Investigating… ${n} ${n === 1 ? "query" : "queries"} · ${Math.round((Date.now() - started) / 1000)}s`;
  }, 500);

  const done = (html) => { clearInterval(timer); turnEl.querySelector(".progress").outerHTML = html; setBusy(false); };
  try {
    const res = await fetch(`/api/conversations/${conversationId}/ask`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let finished = false;
    while (!finished) {
      const { value, done: eof } = await reader.read();
      if (eof) break;
      buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
        const data = chunk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
        if (!data) continue;
        const ev = JSON.parse(data);
        if (ev.type === "tool_call") {
          calls.set(ev.seq, ev);
          const li = document.createElement("li");
          li.innerHTML = `${sysChip(ev.system)} ${esc(TOOL_LABEL[ev.tool] || ev.tool)}`;
          list.appendChild(li);
          while (list.children.length > 5) list.firstChild.remove();
        } else if (ev.type === "answer") {
          done(renderAnswer(ev.turn)); finished = true;
        } else if (ev.type === "error") {
          done(`<div class="a"><p class="headline error">Something went wrong: ${esc(ev.message)}</p></div>`); finished = true;
        }
      }
    }
    if (!finished) done(`<div class="a"><p class="headline error">The connection closed before an answer arrived.</p></div>`);
  } catch (err) {
    done(`<div class="a"><p class="headline error">${esc(err.message)}</p></div>`);
  }
}

document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip && chip.dataset.q) ask(chip.dataset.q);
});
$("form").addEventListener("submit", (e) => { e.preventDefault(); const q = $("input").value; $("input").value = ""; ask(q); });
$("reset").addEventListener("click", () => { if (!busy) newConversation(); });

renderStarters();
loadConfig();
restoreOrStart();
