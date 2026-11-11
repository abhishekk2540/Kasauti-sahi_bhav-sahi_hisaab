"use client";
import { Send, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Empty, ErrorBox, PageHeader, Seg, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, inr, longDate } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import type { InstallmentRow, Reminder } from "@/lib/types";

type Filter = "draft" | "sent" | "failed" | "dismissed";

export default function RemindersPage() {
  const [filter, setFilter] = useState<Filter>("draft");
  const list = useApi<Reminder[]>(`/reminders?status=${filter}`);
  const inst = useApi<{ items: InstallmentRow[] }>("/installments");
  const gen = useAction();
  const [genMsg, setGenMsg] = useState<string | null>(null);

  const generate = () => gen.run(async () => {
    const r = await api<Reminder[]>("/reminders/generate", { method: "POST" });
    setGenMsg(r.length ? `${r.length} new draft(s) created.` : "No new reminders to draft (nothing due in the reminder window, or already drafted).");
    setFilter("draft");
    list.reload();
  });
  const info = (id: number) => inst.data?.items.find((i) => i.installment_id === id);

  return (
    <>
      <PageHeader title="Payment reminders" subtitle="AI drafts a message. You review, edit and send it. Nothing is sent automatically."
        actions={<button className="btn-primary" onClick={generate} disabled={gen.busy}><Sparkles className="h-4 w-4" /> {gen.busy ? "Drafting..." : "Draft reminders"}</button>} />
      {gen.error && <div className="mb-3"><ErrorBox message={gen.error} /></div>}
      {genMsg && <p className="mb-3 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700">{genMsg}</p>}
      <div className="mb-4"><Seg value={filter} onChange={setFilter} options={[["draft", "To review"], ["sent", "Sent"], ["failed", "Failed"], ["dismissed", "Dismissed"]]} /></div>

      {list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : !list.data ? <Spinner /> : list.data.length === 0 ? <Empty>No {filter === "draft" ? "drafts to review" : filter + " reminders"}.</Empty> : (
        <div className="space-y-3">{list.data.map((r) => <ReminderCard key={r.id} r={r} info={info(r.installment_id)} onChange={list.reload} />)}</div>
      )}
    </>
  );
}

function ReminderCard({ r, info, onChange }: { r: Reminder; info?: InstallmentRow; onChange: () => void }) {
  const [text, setText] = useState(r.draft_text);
  const a = useAction();
  const editable = r.status === "draft" || r.status === "failed";
  const dirty = text !== r.draft_text;
  const save = () => a.run(async () => { await api(`/reminders/${r.id}`, { method: "PATCH", body: { draft_text: text } }); onChange(); });
  const send = () => a.run(async () => {
    if (dirty) await api(`/reminders/${r.id}`, { method: "PATCH", body: { draft_text: text } });
    await api(`/reminders/${r.id}/send`, { method: "POST" });
    onChange();
  });
  const dismiss = () => a.run(async () => { await api(`/reminders/${r.id}/dismiss`, { method: "POST" }); onChange(); });

  return (
    <div className="card">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        <div><span className="font-medium">{info?.customer ?? `Instalment #${r.installment_id}`}</span>{info && <span className="text-stone-500"> · {info.scheme} · #{info.number} · {inr(info.amount)} · due {longDate(info.due_date)}</span>}</div>
        <div className="flex items-center gap-2"><span className="badge bg-stone-100 text-stone-600">{r.drafted_by === "ai" ? "AI draft" : "template"}</span><StatusBadge status={r.status} /></div>
      </div>
      <textarea className="input min-h-[96px]" value={text} onChange={(e) => setText(e.target.value)} disabled={!editable} aria-label="Reminder message" maxLength={2000} />
      {r.error && <p className="mt-1 text-xs text-red-700">Last error: {r.error}</p>}
      {r.sent_at && <p className="mt-1 text-xs text-stone-400">Sent {dateTime(r.sent_at + "Z")}</p>}
      {a.error && <div className="mt-2"><ErrorBox message={a.error} /></div>}
      {editable && (
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <button className="btn-danger" onClick={dismiss} disabled={a.busy}><X className="h-4 w-4" /> Dismiss</button>
          {dirty && <button className="btn-ghost" onClick={save} disabled={a.busy}>Save edit</button>}
          <button className="btn-primary" onClick={send} disabled={a.busy || !text.trim()}><Send className="h-4 w-4" /> Send to customer</button>
        </div>
      )}
    </div>
  );
}
