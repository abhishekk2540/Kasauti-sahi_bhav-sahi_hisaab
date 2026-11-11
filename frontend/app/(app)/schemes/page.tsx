"use client";
import { ChevronDown, ChevronRight, Plus, UserPlus } from "lucide-react";
import { useState } from "react";
import { Empty, ErrorBox, Field, Modal, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { inr, longDate, shortDate } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import type { Customer, Enrolment, Installment, InstallmentRow, Scheme } from "@/lib/types";

export default function SchemesPage() {
  const schemes = useApi<Scheme[]>("/schemes");
  const customers = useApi<Customer[]>("/customers");
  const due = useApi<{ count: number; items: InstallmentRow[] }>("/installments?status=pending");
  const [creating, setCreating] = useState(false);
  const [enrolFor, setEnrolFor] = useState<Scheme | null>(null);
  const [pay, setPay] = useState<{ id: number; label: string; amount: number } | null>(null);
  const [version, setVersion] = useState(0);
  const changed = () => { due.reload(); setVersion((v) => v + 1); };

  return (
    <>
      <PageHeader title="Savings schemes" subtitle="Monthly instalment schemes (for example the 11-month plan)"
        actions={<button className="btn-primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New scheme</button>} />

      <section className="mb-8">
        <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Pending payments {due.data ? `(${due.data.count})` : ""}</h2>
        {due.error ? <ErrorBox message={due.error} onRetry={due.reload} /> : !due.data ? <Spinner /> : due.data.items.length === 0 ? <Empty>Nothing pending.</Empty> : (
          <div className="card overflow-x-auto p-0">
            <table className="w-full min-w-[560px]"><thead className="border-b border-stone-200"><tr><th className="th">Customer</th><th className="th">Scheme</th><th className="th">#</th><th className="th">Due</th><th className="th">Amount</th><th className="th" /></tr></thead>
              <tbody className="divide-y divide-stone-100">
                {due.data.items.map((i) => (
                  <tr key={i.installment_id}>
                    <td className="td font-medium">{i.customer}</td><td className="td">{i.scheme}</td><td className="td">{i.number}/{i.of}</td>
                    <td className="td">{longDate(i.due_date)} {i.overdue && <StatusBadge status="overdue" />}</td><td className="td">{inr(i.amount)}</td>
                    <td className="td text-right"><button className="btn-ghost py-1" onClick={() => setPay({ id: i.installment_id, label: `${i.customer} · instalment ${i.number}`, amount: i.amount })}>Record payment</button></td>
                  </tr>
                ))}
              </tbody></table>
          </div>
        )}
      </section>

      <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Your schemes</h2>
      {schemes.error ? <ErrorBox message={schemes.error} onRetry={schemes.reload} /> : !schemes.data ? <Spinner /> : schemes.data.length === 0 ? <Empty>No scheme yet. Create one, then enrol customers.</Empty> : (
        <div className="space-y-3">
          {schemes.data.map((s) => <SchemeCard key={s.id} scheme={s} customers={customers.data || []} version={version} onEnrol={() => setEnrolFor(s)} onPay={(i, who) => setPay({ id: i.id, label: `${who} · instalment ${i.number}`, amount: i.amount })} />)}
        </div>
      )}

      <CreateModal open={creating} onClose={() => setCreating(false)} onSaved={() => { setCreating(false); schemes.reload(); }} />
      <EnrolModal scheme={enrolFor} customers={customers.data || []} onClose={() => setEnrolFor(null)} onSaved={() => { setEnrolFor(null); changed(); }} />
      <PayModal pay={pay} onClose={() => setPay(null)} onSaved={() => { setPay(null); changed(); }} />
    </>
  );
}

function SchemeCard({ scheme, customers, version, onEnrol, onPay }: { scheme: Scheme; customers: Customer[]; version: number; onEnrol: () => void; onPay: (i: Installment, who: string) => void }) {
  const [open, setOpen] = useState(false);
  const { data, error, reload } = useApi<Enrolment[]>(open ? `/schemes/${scheme.id}/enrolments?v=${version}` : null);
  const name = (id: number) => customers.find((c) => c.id === id)?.name ?? `Customer #${id}`;
  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button className="flex items-center gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <div><div className="font-medium">{scheme.name}</div><div className="text-sm text-stone-500">{inr(scheme.monthly_amount)} × {scheme.months} months = {inr(scheme.monthly_amount * scheme.months)}</div></div>
        </button>
        <button className="btn-ghost" onClick={onEnrol}><UserPlus className="h-4 w-4" /> Enrol customer</button>
      </div>
      {open && (
        <div className="mt-4 space-y-4 border-t border-stone-100 pt-4">
          {error ? <ErrorBox message={error} onRetry={reload} /> : !data ? <Spinner /> : data.length === 0 ? <p className="text-sm text-stone-500">No one enrolled yet.</p> : data.map((e) => {
            const paid = e.installments.filter((i) => i.status === "paid").length;
            return (
              <div key={e.id}>
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium">{name(e.customer_id)}</span>
                  <span className="text-stone-500">{paid}/{e.installments.length} paid · matures {longDate(e.maturity_date)}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {e.installments.map((i) => (
                    <button key={i.id} disabled={i.status === "paid"} onClick={() => onPay(i, name(e.customer_id))}
                      title={`#${i.number} due ${shortDate(i.due_date)} · ${inr(i.amount)}${i.status === "paid" ? " · paid" : ""}`}
                      className={`h-9 w-9 rounded-lg border text-xs font-medium ${i.status === "paid" ? "border-emerald-200 bg-emerald-100 text-emerald-800" : "border-stone-300 bg-white hover:border-maroon-500"}`}>{i.number}</button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CreateModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ name: "", monthly_amount: "", months: "11" });
  const a = useAction();
  const submit = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { await api("/schemes", { body: { name: f.name, monthly_amount: Number(f.monthly_amount), months: Number(f.months) } }); setF({ name: "", monthly_amount: "", months: "11" }); onSaved(); }); };
  return (
    <Modal open={open} onClose={onClose} title="New scheme">
      <form onSubmit={submit} className="space-y-3">
        <Field label="Scheme name"><input className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Gold Saver 11-month" autoFocus /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Monthly amount (₹)"><input className="input" type="number" min={1} required value={f.monthly_amount} onChange={(e) => setF({ ...f, monthly_amount: e.target.value })} /></Field>
          <Field label="Months"><input className="input" type="number" min={1} max={60} required value={f.months} onChange={(e) => setF({ ...f, months: e.target.value })} /></Field>
        </div>
        {a.error && <ErrorBox message={a.error} />}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={a.busy}>Create</button></div>
      </form>
    </Modal>
  );
}

function EnrolModal({ scheme, customers, onClose, onSaved }: { scheme: Scheme | null; customers: Customer[]; onClose: () => void; onSaved: () => void }) {
  const [cid, setCid] = useState("");
  const [start, setStart] = useState("");
  const a = useAction();
  const submit = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { await api(`/schemes/${scheme!.id}/enrol`, { body: { customer_id: Number(cid), start_date: start || null } }); setCid(""); setStart(""); onSaved(); }); };
  return (
    <Modal open={!!scheme} onClose={onClose} title={`Enrol in ${scheme?.name ?? ""}`}>
      <form onSubmit={submit} className="space-y-3">
        {customers.length === 0 ? <p className="text-sm text-stone-500">Add a customer first (Customers page).</p> : (
          <>
            <Field label="Customer"><select className="input" required value={cid} onChange={(e) => setCid(e.target.value)}><option value="">Select...</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.phone})</option>)}</select></Field>
            <Field label="First instalment due" hint="Leave empty for today. Later instalments fall on the same day each month."><input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} /></Field>
          </>
        )}
        {a.error && <ErrorBox message={a.error} />}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={a.busy || !cid}>Enrol</button></div>
      </form>
    </Modal>
  );
}

function PayModal({ pay, onClose, onSaved }: { pay: { id: number; label: string; amount: number } | null; onClose: () => void; onSaved: () => void }) {
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const a = useAction();
  const submit = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { await api(`/installments/${pay!.id}/pay`, { body: { amount: amount ? Number(amount) : null, paid_on: date || null } }); setAmount(""); setDate(""); onSaved(); }); };
  return (
    <Modal open={!!pay} onClose={onClose} title="Record payment">
      <form onSubmit={submit} className="space-y-3">
        <p className="text-sm text-stone-600">{pay?.label}</p>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Amount received (₹)" hint={`Due: ${pay ? inr(pay.amount) : ""}`}><input className="input" type="number" min={1} placeholder={String(pay?.amount ?? "")} value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
          <Field label="Paid on" hint="Empty = today"><input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        </div>
        {a.error && <ErrorBox message={a.error} />}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={a.busy}>Mark as paid</button></div>
      </form>
    </Modal>
  );
}
