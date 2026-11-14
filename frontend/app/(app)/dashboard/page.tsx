"use client";
import Link from "next/link";
import { useState } from "react";
import { PriceChart } from "@/components/PriceChart";
import { RateCard } from "@/components/RateCard";
import { Disclaimer, Empty, ErrorBox, PageHeader, Seg, Spinner, Stat, StatusBadge } from "@/components/ui";
import { dateTime, inr } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Dashboard, Margin, Metal } from "@/lib/types";

export default function DashboardPage() {
  const [days, setDays] = useState(30);
  const [metal, setMetal] = useState<Metal>("gold");
  const { data, error, loading, reload } = useApi<Dashboard>(`/dashboard?days=${days}`);
  const margins = useApi<Margin[]>("/margins");

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return <Spinner />;
  const c = data.counts;
  const multiplier = metal === "gold" ? 10 : 1000;
  const series = data.charts[metal].map((p) => ({ date: p.date, value: p.selling_per_gram * multiplier }));

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Your business at a glance" />
      <div className="grid gap-4 sm:grid-cols-2">
        <RateCard metal="gold" snap={data.rates.gold} margin={margins.data?.find((m) => m.metal === "gold")} series={data.charts.gold.map((p) => p.selling_per_gram * 10)} />
        <RateCard metal="silver" snap={data.rates.silver} margin={margins.data?.find((m) => m.metal === "silver")} series={data.charts.silver.map((p) => p.selling_per_gram * 1000)} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Customers" value={c.customers} />
        <Stat label="Active schemes" value={c.active_schemes} sub={`${c.enrolments} enrolments`} />
        <Stat label="Pending installments" value={c.pending_installments} />
        <Stat label="Overdue" value={c.overdue_installments} warn={c.overdue_installments > 0} sub={c.overdue_installments ? inr(c.overdue_amount) : "All on time"} />
      </div>

      <div className="card mt-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-lg font-semibold text-maroon-800">Selling price per gram</h2>
          <div className="flex gap-2">
            <Seg value={metal} onChange={setMetal} options={[["gold", "Gold"], ["silver", "Silver"]]} />
            <Seg value={days} onChange={setDays} options={[[7, "7d"], [30, "30d"], [90, "90d"]]} />
          </div>
        </div>
        {loading ? <Spinner /> : <PriceChart data={series} metal={metal} />}
      </div>

      <div className="card mt-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-maroon-800">Recent alerts</h2>
          <Link href="/alerts" className="text-sm text-maroon-600 underline">Manage ({c.active_rules} active rules)</Link>
        </div>
        {data.recent_alerts.length === 0 ? (
          <Empty>No alerts sent yet. Create a rule on the Alerts page.</Empty>
        ) : (
          <ul className="divide-y divide-stone-100">
            {data.recent_alerts.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-stone-600">Rule #{a.rule_id} via {a.channel}</span>
                <span className="flex items-center gap-3"><StatusBadge status={a.status} /><span className="text-xs text-stone-400">{dateTime(a.created_at)}</span></span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <Disclaimer text={data.disclaimer} />
    </>
  );
}
