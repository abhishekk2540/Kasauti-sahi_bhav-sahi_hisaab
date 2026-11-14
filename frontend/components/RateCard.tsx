"use client";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { inr } from "@/lib/format";
import type { Margin, RateSnapshot } from "@/lib/types";

type Props = {
  metal: "gold" | "silver";
  snap: RateSnapshot | null;
  margin?: Pick<Margin, "margin_percent" | "making_per_gram">;
  series?: number[];
};

export function RateCard({ snap, metal, margin, series = [] }: Props) {
  const isGold = metal === "gold";
  const title = isGold ? "GOLD 24K · PER 10 G" : "SILVER · PER KG";
  const multiplier = isGold ? 10 : 1000;
  const stroke = isGold ? "#c99a2e" : "#8b8a94";

  if (!snap) {
    return (
      <div className="card border-t-4 border-stone-300">
        <div className="label">{title}</div>
        <div className="text-sm text-stone-600">No rate stored yet. Use “Fetch rates now” on the Rates page.</div>
      </div>
    );
  }

  return (
    <div className={`card border-t-4 p-6 ${isGold ? "border-t-gold-500" : "border-t-[#8b8a94]"}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-stone-600">
          <span className={`h-2 w-2 rounded-full ${isGold ? "bg-gold-500" : "bg-[#8b8a94]"}`} />
          {title}
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${snap.stale ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
          {snap.stale ? "Stale" : "Live"}
        </span>
      </div>

      <div className="mt-5">
        <div className="num font-display text-4xl font-bold text-maroon-800 sm:text-5xl">{inr(snap.display_price)}</div>
        <div className="mt-1 text-sm text-stone-600">Your selling rate</div>
      </div>

      <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
        <div className="text-sm text-stone-600">
          <div className="num">Market {inr(snap.market_per_gram * multiplier)}</div>
          {margin && (margin.margin_percent !== 0 || margin.making_per_gram !== 0) && (
            <div className="mt-1 text-xs text-stone-600">
              + {margin.margin_percent}% margin, + {inr(margin.making_per_gram, 2)}/g making
            </div>
          )}
        </div>
        <Sparkline series={series} stroke={stroke} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-stone-200 pt-4">
        <Comparison label="vs 7-day avg" value={snap.pct_below_avg_7d} />
        <Comparison label="vs 30-day avg" value={snap.pct_below_avg_30d} />
      </div>
    </div>
  );
}

function Sparkline({ series, stroke }: { series: number[]; stroke: string }) {
  if (series.length < 2) return null;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const points = series.map((value, index) => {
    const x = (index / (series.length - 1)) * 124;
    const y = 38 - ((value - min) / range) * 36;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg width="124" height="40" viewBox="0 0 124 40" aria-hidden="true">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Comparison({ label, value }: { label: string; value: number | null }) {
  if (value == null) {
    return <div><div className="text-xs text-stone-600">{label}</div><div className="mt-1 text-sm text-stone-500">n/a</div></div>;
  }
  const below = value >= 0;
  const Icon = below ? ArrowDownRight : ArrowUpRight;
  return (
    <div>
      <div className="text-xs text-stone-600">{label}</div>
      <div className={`num mt-1 flex items-center gap-1 text-sm font-semibold ${below ? "text-[#166534]" : "text-[#b42318]"}`}>
        <Icon className="h-4 w-4" /> {Math.abs(value).toFixed(1)}% {below ? "below" : "above"}
      </div>
    </div>
  );
}
