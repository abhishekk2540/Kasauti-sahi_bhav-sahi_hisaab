import { BarChart3 } from "lucide-react";

/** Centered card used by the forgot/reset password pages (matches the login card). */
export function AuthCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-maroon-800 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center gap-2">
          <BarChart3 className="h-7 w-7 text-gold-500" />
          <span className="font-display text-2xl font-semibold text-maroon-800">Kasauti</span>
        </div>
        <h1 className="mb-1 text-lg font-semibold">{title}</h1>
        {subtitle && <p className="mb-5 text-sm text-stone-500">{subtitle}</p>}
        {children}
      </div>
    </div>
  );
}