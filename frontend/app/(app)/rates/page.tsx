"use client";
import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Banner } from "@/components/Banner";
import { PriceChart } from "@/components/PriceChart";
import { RateCard } from "@/components/RateCard";
import { Disclaimer, Empty, ErrorBox, Field, PageHeader, Seg, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, inr } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import type { Margin, MarginChange, Metal, RateSnapshot } from "@/lib/types";

type Today = { disclaimer: string; rates: Record<Metal, RateSnapshot | null> };
type History = { points: { date: string; market_per_gram: number; selling_per_gram: number }[] };

export default function RatesPage() {
  const today = useApi<Today>("/rates/today");
  const margins = useApi<Margin[]>("/margins");
  const log = useApi<MarginChange[]>("/margins/log");
  const [metal, setMetal] = useState<Metal>("gold");
  const [days, setDays] = useState(30);
  const hist = useApi<History>(`/rates/history?metal=${metal}&days=${days}`);
  const [bannerKey, setBannerKey] = useState(0);
  const refresh = useAction();
  const [fetchMsg, setFetchMsg] = useState<string | null>(null);

  const reloadAll = () => { today.reload(); hist.reload(); setBannerKey((k) => k + 1); };

  const fetchNow = () => refresh.run(async () => {
    const r = await api<{ ok: boolean; error?: string; source: string }>("/rates/refresh", { method: "POST" });
    setFetchMsg(r.ok ? `Rates updated (source: ${r.source}).` : `Could not fetch new rates: ${r.error}. Showing last known rates.`);
    reloadAll();
  });

  return (
    <>
      <PageHeader title="Rates & Banner" subtitle="Market rate, your margin, and a shareable daily banner"
        actions={<button className="btn-primary" onClick={fetchNow} disabled={refresh.busy}><RefreshCw className={`h-4 w-4 ${refresh.busy ? "animate-spin" : ""}`} /> Fetch rates now</button>} />
      {refresh.error && <div className="mb-4"><ErrorBox message={refresh.error} /></div>}
      {fetchMsg && <p className="mb-4 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700">{fetchMsg}</p>}

      {today.error ? <ErrorBox message={today.error} onRetry={today.reload} /> : !today.data ? <Spinner /> : (
        <div className="grid gap-4 sm:grid-cols-2">
          <RateCard metal="gold" snap={today.data.rates.gold} />
          <RateCard metal="silver" snap={today.data.rates.silver} />
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-1 font-display text-lg font-semibold text-maroon-800">Your margin</h2>
          <p className="mb-4 text-sm text-stone-500">Added on top of the market rate. The banner and alerts show your selling rate.</p>
          {margins.error ? <ErrorBox message={margins.error} onRetry={margins.reload} /> : !margins.data ? <Spinner /> : (
            <div className="space-y-5">
              {margins.data.map((m) => <MarginForm key={m.metal + m.margin_percent + m.making_per_gram} m={m} onSaved={() => { margins.reload(); log.reload(); reloadAll(); }} />)}
            </div>
          )}
        </div>
        <div className="card">
          <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Today's banner</h2>
          <Banner refreshKey={bannerKey} />
        </div>
      </div>

      <div className="card mt-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-lg font-semibold text-maroon-800">History</h2>
          <div className="flex gap-2">
            <Seg value={metal} onChange={setMetal} options={[["gold", "Gold"], ["silver", "Silver"]]} />
            <Seg value={days} onChange={setDays} options={[[7, "7d"], [30, "30d"], [90, "90d"]]} />
          </div>
        </div>
        {hist.loading && !hist.data ? <Spinner /> : <PriceChart data={(hist.data?.points || []).map((p) => ({ date: p.date, value: p.selling_per_gram }))} />}
      </div>

      <div className="card mt-4">
        <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Margin change log</h2>
        {!log.data ? <Spinner /> : log.data.length === 0 ? <Empty>No margin changes yet.</Empty> : (
          <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className="th">When</th><th className="th">Metal</th><th className="th">Margin %</th><th className="th">Making ₹/g</th></tr></thead>
            <tbody className="divide-y divide-stone-100">
              {log.data.map((c, i) => (
                <tr key={i}><td className="td">{dateTime(c.changed_at + "Z")}</td><td className="td capitalize">{c.metal}</td>
                  <td className="td">{c.old_percent}% → <b>{c.new_percent}%</b></td><td className="td">{inr(c.old_per_gram, 2)} → <b>{inr(c.new_per_gram, 2)}</b></td></tr>
              ))}
            </tbody></table></div>
        )}
      </div>
      <Disclaimer text={today.data?.disclaimer} />
    </>
  );
}

function MarginForm({ m, onSaved }: { m: Margin; onSaved: () => void }) {
  const [pct, setPct] = useState(String(m.margin_percent));
  const [making, setMaking] = useState(String(m.making_per_gram));
  const a = useAction();
  const [saved, setSaved] = useState(false);
  useEffect(() => { setSaved(false); }, [pct, making]);
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    a.run(async () => {
      await api(`/margins/${m.metal}`, { method: "PUT", body: { margin_percent: Number(pct), making_per_gram: Number(making) } });
      setSaved(true);
      onSaved();
    });
  };
  return (
    <form onSubmit={save}>
      <div className="mb-2 text-sm font-medium capitalize">{m.metal}</div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Margin %"><input className="input" type="number" step="0.01" min={-50} max={100} required value={pct} onChange={(e) => setPct(e.target.value)} /></Field>
        <Field label="Making ₹ / gram"><input className="input" type="number" step="0.01" required value={making} onChange={(e) => setMaking(e.target.value)} /></Field>
      </div>
      {a.error && <div className="mt-2"><ErrorBox message={a.error} /></div>}
      <div className="mt-2 flex items-center gap-3">
        <button className="btn-ghost" disabled={a.busy}>{a.busy ? "Saving..." : "Save"}</button>
        {saved && <span className="text-sm text-emerald-700">Saved</span>}
      </div>
    </form>
  );
}
