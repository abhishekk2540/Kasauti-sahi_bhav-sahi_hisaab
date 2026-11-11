"use client";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, shortDate } from "@/lib/format";

export function PriceChart({ data, color = "#8a2a3b", height = 260 }: { data: { date: string; value: number }[]; color?: string; height?: number }) {
  if (data.length < 2) {
    return <div className="flex h-40 items-center justify-center rounded-lg bg-stone-50 text-sm text-stone-500">Not enough history yet. The chart fills in as daily rates are stored.</div>;
  }
  return (
    <div style={{ height }} role="img" aria-label="Price history chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#eee8dd" vertical={false} />
          <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 11, fill: "#78716c" }} minTickGap={24} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#78716c" }} width={64} tickFormatter={(v: number) => inr(v)} />
          <Tooltip formatter={(v) => [inr(Number(v), 2), "per gram"]} labelFormatter={(l) => shortDate(String(l))} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
