"use client";
import { Copy, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Empty, ErrorBox, Field, Modal, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const { data, error, loading, reload } = useApi<Customer[]>(`/customers${dq ? `?q=${encodeURIComponent(dq)}` : ""}`);
  const [editing, setEditing] = useState<Customer | "new" | null>(null);
  const act = useAction();

  const toggleOptOut = (c: Customer) => act.run(async () => { await api(`/customers/${c.id}`, { method: "PATCH", body: { opted_out: !c.opted_out } }); reload(); });
  const remove = (c: Customer) => {
    if (!confirm(`Delete ${c.name}?`)) return;
    act.run(async () => { await api(`/customers/${c.id}`, { method: "DELETE" }); reload(); });
  };
  const copy = async (c: Customer) => {
    if (!c.telegram_link) return alert("Set TELEGRAM_BOT_USERNAME on the backend to get invite links.");
    await navigator.clipboard.writeText(c.telegram_link);
    alert(`Invite link copied. Send it to ${c.name} so they can receive updates on Telegram.`);
  };

  return (
    <>
      <PageHeader title="Customers" subtitle="People you send rate alerts and scheme reminders to"
        actions={<button className="btn-primary" onClick={() => setEditing("new")}><Plus className="h-4 w-4" /> Add customer</button>} />
      <div className="relative mb-4 max-w-sm">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
        <input className="input pl-9" placeholder="Search name or phone" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search customers" />
      </div>
      {act.error && <div className="mb-3"><ErrorBox message={act.error} /></div>}
      {error ? <ErrorBox message={error} onRetry={reload} /> : !data ? <Spinner /> : data.length === 0 ? (
        <Empty>{dq ? "No customer matches your search." : "No customers yet. Add your first one."}</Empty>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[640px]">
            <thead className="border-b border-stone-200"><tr><th className="th">Name</th><th className="th">Phone</th><th className="th">Telegram</th><th className="th">Updates</th><th className="th" /></tr></thead>
            <tbody className="divide-y divide-stone-100">
              {data.map((c) => (
                <tr key={c.id} className={loading ? "opacity-60" : ""}>
                  <td className="td font-medium">{c.name}</td>
                  <td className="td">{c.phone}</td>
                  <td className="td">{c.telegram_linked ? <span className="badge bg-emerald-100 text-emerald-800">linked</span> : <button className="inline-flex items-center gap-1 text-xs text-maroon-600 underline" onClick={() => copy(c)}><Copy className="h-3 w-3" /> copy invite link</button>}</td>
                  <td className="td">
                    <button onClick={() => toggleOptOut(c)} className={`badge ${c.opted_out ? "bg-stone-200 text-stone-700" : "bg-emerald-100 text-emerald-800"}`} title="Click to toggle">{c.opted_out ? "opted out" : "subscribed"}</button>
                  </td>
                  <td className="td text-right">
                    <button aria-label={`Edit ${c.name}`} className="rounded p-1.5 text-stone-500 hover:bg-stone-100" onClick={() => setEditing(c)}><Pencil className="h-4 w-4" /></button>
                    <button aria-label={`Delete ${c.name}`} className="rounded p-1.5 text-red-600 hover:bg-red-50" onClick={() => remove(c)}><Trash2 className="h-4 w-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-stone-400">Customers must press Start on your Telegram bot (using their invite link) before they can receive messages. They can send /stop to unsubscribe.</p>
      <CustomerModal editing={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />
    </>
  );
}

function CustomerModal({ editing, onClose, onSaved }: { editing: Customer | "new" | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const a = useAction();
  useEffect(() => {
    if (editing && editing !== "new") { setName(editing.name); setPhone(editing.phone); } else { setName(""); setPhone(""); }
    a.setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing]);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    a.run(async () => {
      if (editing === "new") await api("/customers", { body: { name, phone } });
      else if (editing) await api(`/customers/${editing.id}`, { method: "PATCH", body: { name, phone } });
      onSaved();
    });
  };
  return (
    <Modal open={!!editing} onClose={onClose} title={editing === "new" ? "Add customer" : "Edit customer"}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Name"><input className="input" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} autoFocus /></Field>
        <Field label="Phone"><input className="input" required pattern="[0-9+\- ]{7,20}" title="7-20 digits, may start with +" maxLength={20} inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
        {a.error && <ErrorBox message={a.error} />}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={a.busy}>{a.busy ? "Saving..." : "Save"}</button></div>
      </form>
    </Modal>
  );
}
