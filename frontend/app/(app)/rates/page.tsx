"use client";
import { Check, RefreshCw } from "lucide-react";
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

  const historyData = (hist.data?.points || []).map((p) => ({ date: p.date, value: p.selling_per_gram * (metal === "gold" ? 10 : 1000) }));
  const historySeries = historyData.map((p) => p.value);

  return (
    <>
      <PageHeader
        title="Rates & Banner"
        subtitle="Market rate, your margin, and a shareable daily banner"
        actions={
          <div className="flex flex-wrap items-center justify-end gap-3">
            {today.data?.rates.gold?.as_of && <span className="flex items-center gap-2 text-sm text-stone-600"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Updated {dateTime(today.data.rates.gold.as_of)}</span>}
            <button className="btn-primary" onClick={fetchNow} disabled={refresh.busy}><RefreshCw className={`h-4 w-4 ${refresh.busy ? "animate-spin" : ""}`} /> Fetch rates now</button>
          </div>
        }
      />
      {refresh.error && <div className="mb-4"><ErrorBox message={refresh.error} /></div>}
      {fetchMsg && <p className="mb-4 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700">{fetchMsg}</p>}

      {today.error ? <ErrorBox message={today.error} onRetry={today.reload} /> : !today.data ? <Spinner /> : (
        <div className="grid gap-4 sm:grid-cols-2">
          <RateCard metal="gold" snap={today.data.rates.gold} margin={margins.data?.find((m) => m.metal === "gold")} series={metal === "gold" ? historySeries : []} />
          <RateCard metal="silver" snap={today.data.rates.silver} margin={margins.data?.find((m) => m.metal === "silver")} series={metal === "silver" ? historySeries : []} />
        </div>
      )}

      <div className="mt-4 grid items-stretch gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-1 font-display text-lg font-semibold text-maroon-800">Your margin</h2>
          <p className="mb-4 text-sm text-stone-600">Added on top of the market rate. The banner and alerts show your selling rate.</p>
          {margins.error ? <ErrorBox message={margins.error} onRetry={margins.reload} /> : !margins.data || !today.data ? <Spinner /> : (
            <MarginEditor
              metal={metal}
              setMetal={setMetal}
              margins={margins.data}
              snapshot={today.data.rates[metal]}
              onSaved={() => { margins.reload(); log.reload(); reloadAll(); }}
            />
          )}
        </div>
        <div className="card">
          <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Today's banner</h2>
          <div className="mx-auto max-w-[300px]"><Banner refreshKey={bannerKey} /></div>
        </div>
      </div>

      <div className="card mt-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-lg font-semibold text-maroon-800">Price history · {metal === "gold" ? "Gold, per 10 g" : "Silver, per kg"}</h2>
          <div className="flex gap-2">
            <Seg value={metal} onChange={setMetal} options={[["gold", "Gold"], ["silver", "Silver"]]} />
            <Seg value={days} onChange={setDays} options={[[7, "7d"], [30, "30d"], [90, "90d"]]} />
          </div>
        </div>
        {hist.loading && !hist.data ? <Spinner /> : <PriceChart metal={metal} data={historyData} />}
      </div>

      <div className="card mt-4">
        <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Margin change log</h2>
        {!log.data ? <Spinner /> : log.data.length === 0 ? <Empty>No margin changes yet. Changes appear here with the date and old → new values.</Empty> : (
          <div className="overflow-x-auto"><table className="w-full"><thead><tr><th className="th">When</th><th className="th">Metal</th><th className="th">Margin %</th><th className="th">Making ₹/g</th></tr></thead>
            <tbody className="divide-y divide-stone-100">
              {log.data.map((c, i) => <tr key={i}><td className="td">{dateTime(c.changed_at + "Z")}</td><td className="td capitalize">{c.metal}</td><td className="td">{c.old_percent}% → <b>{c.new_percent}%</b></td><td className="td">{inr(c.old_per_gram, 2)} → <b>{inr(c.new_per_gram, 2)}</b></td></tr>)}
            </tbody>
          </table></div>
        )}
      </div>
      <Disclaimer text={today.data?.disclaimer} />
    </>
  );
}

function MarginEditor({ metal, setMetal, margins, snapshot, onSaved }: {
  metal: Metal;
  setMetal: (metal: Metal) => void;
  margins: Margin[];
  snapshot: RateSnapshot | null;
  onSaved: () => void;
}) {
  const current = margins.find((m) => m.metal === metal) || { metal, margin_percent: 0, making_per_gram: 0 };
  const [pct, setPct] = useState(String(current.margin_percent));
  const [making, setMaking] = useState(String(current.making_per_gram));
  const [saved, setSaved] = useState(false);
  const action = useAction();

  useEffect(() => {
    setPct(String(current.margin_percent));
    setMaking(String(current.making_per_gram));
    setSaved(false);
  }, [metal, current.margin_percent, current.making_per_gram]);

  const selectMetal = (value: Metal) => { setMetal(value); };
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    action.run(async () => {
      await api(`/margins/${metal}`, { method: "PUT", body: { margin_percent: Number(pct), making_per_gram: Number(making) } });
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
      onSaved();
    });
  };

  const multiplier = metal === "gold" ? 10 : 1000;
  const base = (snapshot?.market_per_gram || 0) * multiplier;
  const margin = base * (Number(pct) || 0) / 100;
  const makingTotal = (Number(making) || 0) * multiplier;

  return (
    <form onSubmit={save} className="space-y-4">
      <Seg value={metal} onChange={selectMetal} options={[["gold", "Gold"], ["silver", "Silver"]]} />
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Margin %"><div className="relative"><input className="input pr-9 num" type="number" step="0.01" min={-50} max={100} required value={pct} onChange={(e) => setPct(e.target.value)} /><span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-stone-600">%</span></div></Field>
        <Field label="Making charge per gram"><div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-stone-600">₹</span><input className="input pl-8 num" type="number" step="0.01" required value={making} onChange={(e) => setMaking(e.target.value)} /></div></Field>
      </div>
      <div className="rounded-xl border border-[#f1deaa] bg-[#fdf8ec] p-4">
        <div className="mb-3 text-sm font-semibold text-maroon-800">Live preview</div>
        <PreviewRow label="Market rate" value={inr(base)} />
        <PreviewRow label={`+ Margin ${Number(pct) || 0}%`} value={inr(margin)} />
        <PreviewRow label={`+ Making ${inr(Number(making) || 0, 2)} × ${metal === "gold" ? "10 g" : "1 kg"}`} value={inr(makingTotal)} />
        <div className="my-3 border-t border-[#f1deaa]" />
        <div className="flex items-center justify-between"><span className="font-semibold text-stone-700">Your selling rate</span><span className="num font-display text-2xl font-bold text-maroon-800">{inr(base + margin + makingTotal)}</span></div>
      </div>
      {action.error && <ErrorBox message={action.error} />}
      <div className="flex items-center gap-3"><button className="btn-primary" disabled={action.busy}>{action.busy ? "Saving..." : "Save margin"}</button>{saved && <span className="flex items-center gap-1 text-sm font-medium text-emerald-700"><Check className="h-4 w-4" /> Saved</span>}</div>
    </form>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between py-1 text-sm text-stone-700"><span>{label}</span><span className="num">{value}</span></div>;
}
