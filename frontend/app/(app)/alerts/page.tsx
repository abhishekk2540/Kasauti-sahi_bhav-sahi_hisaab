"use client";
import { FlaskConical, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Empty, ErrorBox, Field, Modal, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, inr } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import type { Delivery, Metal, Rule } from "@/lib/types";

interface TestResult { triggered: boolean; reason: string; current_per_gram: number; avg_per_gram: number | null; pct_below_avg: number | null; message_preview: string }

const describe = (r: Rule) =>
  r.kind === "below_avg_pct" ? `${r.metal} is ${r.threshold}% below its ${r.window_days}-day average` : `${r.metal} falls to ${inr(r.threshold)}/g or less`;

export default function AlertsPage() {
  const rules = useApi<Rule[]>("/alerts/rules");
  const deliveries = useApi<Delivery[]>("/alerts/deliveries");
  const [open, setOpen] = useState(false);
  const [test, setTest] = useState<{ rule: Rule; res: TestResult } | null>(null);
  const act = useAction();

  const toggle = (r: Rule) => act.run(async () => { await api(`/alerts/rules/${r.id}`, { method: "PATCH", body: { active: !r.active } }); rules.reload(); });
  const remove = (r: Rule) => { if (confirm(`Delete rule “${r.name}”?`)) act.run(async () => { await api(`/alerts/rules/${r.id}`, { method: "DELETE" }); rules.reload(); deliveries.reload(); }); };
  const dry = (r: Rule) => act.run(async () => setTest({ rule: r, res: await api<TestResult>(`/alerts/rules/${r.id}/test`, { method: "POST" }) }));

  return (
    <>
      <PageHeader title="Price alerts" subtitle="Rules are checked once a day by plain code (no AI). A message goes out only when a rule triggers."
        actions={<button className="btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New rule</button>} />
      {act.error && <div className="mb-3"><ErrorBox message={act.error} /></div>}

      {rules.error ? <ErrorBox message={rules.error} onRetry={rules.reload} /> : !rules.data ? <Spinner /> : rules.data.length === 0 ? (
        <Empty>No rules yet. Example: “silver is 3% below its 30-day average”.</Empty>
      ) : (
        <div className="space-y-3">
          {rules.data.map((r) => (
            <div key={r.id} className="card flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 font-medium">{r.name} {!r.active && <span className="badge bg-stone-200 text-stone-600">paused</span>}</div>
                <div className="text-sm text-stone-600">Alert when {describe(r)}</div>
                <div className="mt-1 text-xs text-stone-400">To: {r.audience === "self" ? "you" : "all subscribed customers"} · cooldown {r.cooldown_hours}h{r.last_triggered_at ? ` · last sent ${dateTime(r.last_triggered_at + "Z")}` : ""}</div>
              </div>
              <div className="flex gap-2">
                <button className="btn-ghost" onClick={() => dry(r)} disabled={act.busy}><FlaskConical className="h-4 w-4" /> Test now</button>
                <button className="btn-ghost" onClick={() => toggle(r)}>{r.active ? "Pause" : "Resume"}</button>
                <button aria-label={`Delete ${r.name}`} className="btn-danger px-2.5" onClick={() => remove(r)}><Trash2 className="h-4 w-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-8 font-display text-lg font-semibold text-maroon-800">Delivery log</h2>
      {!deliveries.data ? <Spinner /> : deliveries.data.length === 0 ? <Empty>Nothing sent yet.</Empty> : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[560px]"><thead className="border-b border-stone-200"><tr><th className="th">When</th><th className="th">Rule</th><th className="th">To</th><th className="th">Status</th><th className="th">Detail</th></tr></thead>
            <tbody className="divide-y divide-stone-100">
              {deliveries.data.map((d) => (
                <tr key={d.id}><td className="td">{dateTime(d.created_at + "Z")}</td><td className="td">#{d.rule_id}</td><td className="td">{d.customer_id ? `Customer #${d.customer_id}` : "You"}</td>
                  <td className="td"><StatusBadge status={d.status} /></td><td className="td text-xs text-stone-500">{d.error || d.channel}</td></tr>
              ))}
            </tbody></table>
        </div>
      )}

      <RuleModal open={open} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); rules.reload(); }} />
      <Modal open={!!test} onClose={() => setTest(null)} title={`Test: ${test?.rule.name ?? ""}`}>
        {test && (
          <div className="space-y-3 text-sm">
            <div className={`rounded-lg p-3 ${test.res.triggered ? "bg-emerald-50 text-emerald-900" : "bg-stone-100 text-stone-700"}`}>
              <b>{test.res.triggered ? "Would trigger right now" : "Would not trigger right now"}</b>
              <div className="mt-1 text-xs">{test.res.reason}</div>
            </div>
            <div className="text-xs text-stone-500">This is a dry run. Nothing was sent. Message preview:</div>
            <pre className="whitespace-pre-wrap rounded-lg bg-stone-50 p-3 text-xs">{test.res.message_preview}</pre>
          </div>
        )}
      </Modal>
    </>
  );
}

function RuleModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const blank = { name: "", metal: "silver" as Metal, kind: "below_avg_pct", window_days: 30, threshold: "3", audience: "self", cooldown_hours: 24 };
  const [f, setF] = useState(blank);
  const a = useAction();
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    a.run(async () => {
      await api("/alerts/rules", { body: { ...f, threshold: Number(f.threshold), window_days: Number(f.window_days), cooldown_hours: Number(f.cooldown_hours) } });
      setF(blank);
      onSaved();
    });
  };
  const pctKind = f.kind === "below_avg_pct";
  return (
    <Modal open={open} onClose={onClose} title="New alert rule">
      <form onSubmit={submit} className="space-y-3">
        <Field label="Rule name"><input className="input" required maxLength={120} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Silver dip" autoFocus /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Metal"><select className="input" value={f.metal} onChange={(e) => setF({ ...f, metal: e.target.value as Metal })}><option value="gold">Gold</option><option value="silver">Silver</option></select></Field>
          <Field label="Trigger"><select className="input" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value, threshold: e.target.value === "below_avg_pct" ? "3" : "" })}><option value="below_avg_pct">% below average</option><option value="below_price">Price at or below</option></select></Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label={pctKind ? "Percent below" : "Price per gram (₹, market rate)"}><input className="input" type="number" step="0.01" min="0.01" max={pctKind ? 99.9 : undefined} required value={f.threshold} onChange={(e) => setF({ ...f, threshold: e.target.value })} /></Field>
          {pctKind && <Field label="Average over"><select className="input" value={f.window_days} onChange={(e) => setF({ ...f, window_days: Number(e.target.value) })}><option value={7}>7 days</option><option value={30}>30 days</option></select></Field>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Send to"><select className="input" value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}><option value="self">Only me</option><option value="customers">All subscribed customers</option></select></Field>
          <Field label="Cooldown (hours)" hint="Minimum gap between sends"><input className="input" type="number" min={1} max={720} value={f.cooldown_hours} onChange={(e) => setF({ ...f, cooldown_hours: Number(e.target.value) })} /></Field>
        </div>
        {a.error && <ErrorBox message={a.error} />}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={a.busy}>{a.busy ? "Saving..." : "Create rule"}</button></div>
      </form>
    </Modal>
  );
}
