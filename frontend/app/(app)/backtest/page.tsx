"use client";
import { useState } from "react";
import { Disclaimer, ErrorBox, Field, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import { useAction } from "@/lib/hooks";
import type { Backtest, StrategyResult } from "@/lib/types";

export default function BacktestPage() {
  const [f, setF] = useState({ metal: "gold", daily_amount: "100", dip_pct: "3", window: "30", gst_pct: "3", spread_pct: "2" });
  const [res, setRes] = useState<Backtest | null>(null);
  const a = useAction();
  const run = (e: React.FormEvent) => {
    e.preventDefault();
    a.run(async () => setRes(await api<Backtest>(`/backtest?${new URLSearchParams(f).toString()}`)));
  };
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <>
      <PageHeader title="Backtest" subtitle="Does buying only on dips beat buying a fixed amount every day? Tested on your stored price history, including GST and dealer spread." />
      <form onSubmit={run} className="card grid gap-3 sm:grid-cols-3">
        <Field label="Metal"><select className="input" value={f.metal} onChange={set("metal")}><option value="gold">Gold</option><option value="silver">Silver</option></select></Field>
        <Field label="Daily amount (₹)"><input className="input" type="number" min={1} value={f.daily_amount} onChange={set("daily_amount")} /></Field>
        <Field label="Dip trigger (%)" hint="Buy when price is this far below average"><input className="input" type="number" step="0.1" min={0.1} max={49} value={f.dip_pct} onChange={set("dip_pct")} /></Field>
        <Field label="Average window (days)"><input className="input" type="number" min={7} max={90} value={f.window} onChange={set("window")} /></Field>
        <Field label="GST (%)"><input className="input" type="number" step="0.1" min={0} max={28} value={f.gst_pct} onChange={set("gst_pct")} /></Field>
        <Field label="Dealer spread (%)"><input className="input" type="number" step="0.1" min={0} max={20} value={f.spread_pct} onChange={set("spread_pct")} /></Field>
        <div className="sm:col-span-3"><button className="btn-primary" disabled={a.busy}>{a.busy ? "Running..." : "Run backtest"}</button></div>
      </form>
      {a.error && <div className="mt-4"><ErrorBox message={a.error} /></div>}
      {a.busy && !res && <Spinner />}
      {res && (
        <div className="mt-4 space-y-4">
          <div className="card border-gold-300 bg-gold-50">
            <div className="font-medium text-maroon-800">{res.verdict}</div>
            <div className="mt-1 text-xs text-stone-500">{res.assumptions.days} days of {res.metal} data ({res.from} to {res.to}). {res.assumptions.note}</div>
          </div>
          <div className="card overflow-x-auto p-0">
            <table className="w-full min-w-[480px]">
              <thead className="border-b border-stone-200"><tr><th className="th" /><th className="th">Daily autopay</th><th className="th">Dip rule</th></tr></thead>
              <tbody className="divide-y divide-stone-100">
                <Row label="Money put in" a={res.daily_autopay} b={res.dip_rule} f={(s) => inr(s.budget)} />
                <Row label="Spent on metal" a={res.daily_autopay} b={res.dip_rule} f={(s) => inr(s.spent)} />
                <Row label="Cash left unspent" a={res.daily_autopay} b={res.dip_rule} f={(s) => inr(s.unspent_cash)} />
                <Row label="Grams bought" a={res.daily_autopay} b={res.dip_rule} f={(s) => s.grams.toFixed(3)} />
                <Row label="Average cost / gram" a={res.daily_autopay} b={res.dip_rule} f={(s) => inr(s.avg_cost_per_gram, 2)} />
                <Row label="Number of purchases" a={res.daily_autopay} b={res.dip_rule} f={(s) => String(s.buys)} />
                <Row label="Value today" a={res.daily_autopay} b={res.dip_rule} f={(s) => inr(s.final_value)} />
                <Row label="Return after costs" a={res.daily_autopay} b={res.dip_rule} f={(s) => `${s.return_pct.toFixed(2)}%`} bold />
              </tbody>
            </table>
          </div>
          <p className="text-xs text-stone-400">Assumptions: GST {res.assumptions.gst_pct}% and dealer spread {res.assumptions.spread_pct}% on every purchase; unspent cash earns nothing. Short histories give unreliable results.</p>
        </div>
      )}
      <Disclaimer />
    </>
  );
}

function Row({ label, a, b, f, bold }: { label: string; a: StrategyResult; b: StrategyResult; f: (s: StrategyResult) => string; bold?: boolean }) {
  return <tr className={bold ? "bg-stone-50 font-semibold" : ""}><td className="td text-stone-500">{label}</td><td className="td">{f(a)}</td><td className="td">{f(b)}</td></tr>;
}
