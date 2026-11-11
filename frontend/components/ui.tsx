"use client";
import { AlertTriangle, Loader2, X } from "lucide-react";
import { useEffect } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-stone-500">
      <Loader2 className="h-4 w-4 animate-spin" /> {label || "Loading..."}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button className="font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-2xl font-semibold text-maroon-800">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-stone-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-stone-300 p-8 text-center text-sm text-stone-500">{children}</div>;
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className="max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:max-w-lg sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-maroon-800">{title}</h2>
          <button aria-label="Close" onClick={onClose} className="rounded p-1 text-stone-500 hover:bg-stone-100">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-stone-400">{hint}</span>}
    </label>
  );
}

const tone: Record<string, string> = {
  sent: "bg-emerald-100 text-emerald-800", paid: "bg-emerald-100 text-emerald-800", confirmed: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800", overdue: "bg-red-100 text-red-800",
  skipped: "bg-stone-100 text-stone-600", dismissed: "bg-stone-100 text-stone-600", cancelled: "bg-stone-100 text-stone-600",
  pending: "bg-amber-100 text-amber-800", draft: "bg-amber-100 text-amber-800",
};
export const StatusBadge = ({ status }: { status: string }) => <span className={`badge ${tone[status] || "bg-stone-100 text-stone-700"}`}>{status}</span>;

export function Disclaimer({ text }: { text?: string }) {
  return <p className="mt-6 text-xs text-stone-400">{text || "Rates are indicative only and not investment advice. Final price is set by the shop at the time of purchase."}</p>;
}

export function Stat({ label, value, sub, warn }: { label: string; value: React.ReactNode; sub?: React.ReactNode; warn?: boolean }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={`font-display text-2xl font-semibold ${warn ? "text-red-700" : "text-maroon-800"}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-stone-500">{sub}</div>}
    </div>
  );
}

export function Seg<T extends string | number>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: [T, string][] }) {
  return (
    <div className="inline-flex overflow-hidden rounded-lg border border-stone-300 text-sm">
      {options.map(([v, label]) => (
        <button key={String(v)} onClick={() => onChange(v)} aria-pressed={v === value} className={`px-3 py-1.5 ${v === value ? "bg-maroon-600 text-white" : "bg-white text-stone-600 hover:bg-stone-50"}`}>{label}</button>
      ))}
    </div>
  );
}
