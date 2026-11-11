"use client";
import { AlertTriangle, TrendingDown, TrendingUp } from "lucide-react";
import { dateTime, inr } from "@/lib/format";
import type { RateSnapshot } from "@/lib/types";

export function RateCard({ snap, metal }: { snap: RateSnapshot | null; metal: "gold" | "silver" }) {
  const title = metal === "gold" ? "Gold 24K" : "Silver";
  if (!snap) {
    return (
      <div className="card">
        <div className="label">{title}</div>
        <div className="text-sm text-stone-500">No rate stored yet. Use “Fetch rates now” on the Rates page.</div>
      </div>
    );
  }
  const d30 = snap.pct_below_avg_30d;
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="label">{title} · per {snap.display_unit}</div>
        {snap.stale && (
          <span className="badge bg-amber-100 text-amber-800" title="The last successful fetch is old. This is the last known rate.">
            <AlertTriangle className="mr-1 h-3 w-3" /> stale
          </span>
        )}
      </div>
      <div className="font-display text-3xl font-semibold text-maroon-800">{inr(snap.display_price)}</div>
      <div className="mt-1 text-xs text-stone-500">Market {inr(snap.market_per_gram, 2)}/g · as of {dateTime(snap.as_of)}</div>
      <div className="mt-3 flex gap-4 text-sm">
        <Cmp label="vs 7-day avg" v={snap.pct_below_avg_7d} />
        <Cmp label="vs 30-day avg" v={d30} />
      </div>
    </div>
  );
}

function Cmp({ label, v }: { label: string; v: number | null }) {
  if (v == null) return <div><div className="text-xs text-stone-400">{label}</div><div className="text-stone-400">n/a</div></div>;
  const below = v >= 0;
  const Icon = below ? TrendingDown : TrendingUp;
  return (
    <div>
      <div className="text-xs text-stone-400">{label}</div>
      <div className={`flex items-center gap-1 font-medium ${below ? "text-emerald-700" : "text-red-700"}`}>
        <Icon className="h-4 w-4" /> {Math.abs(v).toFixed(1)}% {below ? "below" : "above"}
      </div>
    </div>
  );
}
