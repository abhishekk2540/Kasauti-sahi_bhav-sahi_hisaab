"use client";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, shortDate } from "@/lib/format";

type Point = { date: string; value: number };

export function PriceChart({ data, metal, height = 260 }: { data: Point[]; metal: "gold" | "silver"; height?: number }) {
  if (data.length < 2) {
    return <div className="flex min-h-[160px] items-center justify-center rounded-xl bg-stone-50 text-sm text-stone-600">Not enough history yet. The chart fills in as daily rates are stored.</div>;
  }

  const isGold = metal === "gold";
  const lineColor = isGold ? "#b8891f" : "#6b7280";
  const fillColor = isGold ? "#c99a2e" : "#8b8a94";
  const latest = data[data.length - 1];
  const first = data[0];
  const change = first.value === 0 ? 0 : ((latest.value - first.value) / first.value) * 100;
  const high = data.reduce((best, point) => point.value > best.value ? point : best, data[0]);
  const low = data.reduce((best, point) => point.value < best.value ? point : best, data[0]);

  return (
    <div role="img" aria-label="Price history chart">
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <ChartStat label="Latest" value={inr(latest.value)} />
        <ChartStat label={`${data.length}-day change`} value={`${change >= 0 ? "+" : ""}${change.toFixed(1)}%`} tone={change > 0 ? "up" : change < 0 ? "down" : undefined} />
        <ChartStat label="High" value={inr(high.value)} detail={shortDate(high.date)} />
        <ChartStat label="Low" value={inr(low.value)} detail={shortDate(low.date)} />
      </div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={`price-fill-${metal}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={fillColor} stopOpacity={0.38} />
                <stop offset="100%" stopColor={fillColor} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#eee8dd" vertical={false} />
            <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12, fill: "#6b645c" }} minTickGap={32} />
            <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12, fill: "#6b645c" }} width={72} tickFormatter={(value: number) => inr(value).replace("₹", "")} />
            <Tooltip
              cursor={{ stroke: "#6e1f2e", strokeDasharray: "4 4" }}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div className="rounded-lg bg-[#3f111a] p-3 shadow-lg">
                    <div className="text-xs text-[#e8bcc3]">{shortDate(String(label))}</div>
                    <div className="num mt-1 font-semibold text-white">{inr(Number(payload[0].value))}</div>
                  </div>
                );
              }}
            />
            <Area
              type="linear"
              dataKey="value"
              stroke={lineColor}
              strokeWidth={2.5}
              fill={`url(#price-fill-${metal})`}
              dot={(props) => props.index === data.length - 1 ? <circle cx={props.cx} cy={props.cy} r={4} fill="#6e1f2e" /> : null}
              activeDot={{ r: 5, fill: "#fff", stroke: "#6e1f2e", strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ChartStat({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: "up" | "down" }) {
  return (
    <div className="rounded-xl bg-[#faf7f2] p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-stone-600">{label}</div>
      <div className={`num mt-1 text-sm font-semibold ${tone === "up" ? "text-[#b42318]" : tone === "down" ? "text-[#166534]" : "text-maroon-800"}`}>{value}</div>
      {detail && <div className="mt-0.5 text-xs text-stone-600">{detail}</div>}
    </div>
  );
}
