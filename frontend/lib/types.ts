export type Metal = "gold" | "silver";

export interface RateSnapshot {
  metal: Metal;
  market_per_gram: number;
  selling_per_gram: number;
  display_price: number;
  display_unit: string;
  rate_date: string;
  as_of: string;
  source: string;
  stale: boolean;
  avg_7d: number | null;
  pct_below_avg_7d: number | null;
  avg_30d: number | null;
  pct_below_avg_30d: number | null;
}

export interface Me {
  id: number;
  email: string;
  phone: string | null;
  shop_name: string;
  has_logo: boolean;
  telegram_linked: boolean;
  telegram_link: string | null;
}

export interface Dashboard {
  disclaimer: string;
  rates: Record<Metal, RateSnapshot | null>;
  charts: Record<Metal, { date: string; selling_per_gram: number }[]>;
  counts: {
    customers: number; active_schemes: number; enrolments: number; pending_installments: number;
    overdue_installments: number; overdue_amount: number; active_rules: number;
  };
  recent_alerts: { id: number; rule_id: number; status: string; channel: string; created_at: string }[];
}

export interface Customer { id: number; name: string; phone: string; opted_out: boolean; telegram_linked: boolean; telegram_link: string | null }
export interface Margin { metal: Metal; margin_percent: number; making_per_gram: number }
export interface MarginChange { metal: string; old_percent: number; new_percent: number; old_per_gram: number; new_per_gram: number; changed_at: string }

export interface Rule {
  id: number; name: string; metal: Metal; kind: "below_avg_pct" | "below_price"; window_days: 7 | 30;
  threshold: number; audience: "self" | "customers"; cooldown_hours: number; active: boolean; last_triggered_at: string | null;
}
export interface Delivery { id: number; rule_id: number; customer_id: number | null; channel: string; status: string; message: string; error: string | null; created_at: string }

export interface Scheme { id: number; name: string; monthly_amount: number; months: number; active: boolean }
export interface Installment { id: number; number: number; due_date: string; amount: number; status: "pending" | "paid"; paid_at: string | null; paid_amount: number | null }
export interface Enrolment { id: number; customer_id: number; start_date: string; maturity_date: string; installments: Installment[] }
export interface InstallmentRow {
  installment_id: number; customer: string; customer_phone: string; scheme: string; number: number; of: number;
  due_date: string; amount: number; status: string; overdue: boolean;
}
export interface Reminder { id: number; installment_id: number; draft_text: string; drafted_by: string; status: string; error: string | null; created_at: string; sent_at: string | null }

export interface StrategyResult {
  name: string; budget: number; spent: number; unspent_cash: number; grams: number; avg_cost_per_gram: number | null;
  final_value: number; return_pct: number; buys: number;
}
export interface Backtest {
  metal: Metal; from: string; to: string; verdict: string;
  assumptions: { daily_amount: number; dip_pct: number; window_days: number; gst_pct: number; spread_pct: number; days: number; note: string };
  daily_autopay: StrategyResult; dip_rule: StrategyResult;
}
