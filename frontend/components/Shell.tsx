"use client";
import { BarChart3, Bell, Bot, Coins, FlaskConical, Gem, LayoutDashboard, LogOut, Menu, MessageSquare, Settings, Users, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/rates", label: "Rates & Banner", icon: Coins },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/schemes", label: "Schemes", icon: Gem },
  { href: "/reminders", label: "Reminders", icon: MessageSquare },
  { href: "/assistant", label: "AI Assistant", icon: Bot },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { me, loading, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);
  useEffect(() => setOpen(false), [path]);

  if (loading || !me) return <div className="p-8"><Spinner /></div>;

  const nav = (
    <nav className="flex flex-1 flex-col gap-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = path === href || path.startsWith(href + "/");
        return (
          <Link key={href} href={href} className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${active ? "bg-gold-400 font-medium text-maroon-900" : "text-maroon-100 hover:bg-maroon-700"}`}>
            <Icon className="h-4 w-4" /> {label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-60 shrink-0 flex-col bg-maroon-800 p-4 lg:flex">
        <Brand name={me.shop_name} />
        {nav}
        <button onClick={logout} className="mt-4 flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-maroon-200 hover:bg-maroon-700">
          <LogOut className="h-4 w-4" /> Log out
        </button>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-maroon-800 px-4 py-3 lg:hidden">
        <Brand name={me.shop_name} compact />
        <button aria-label="Open menu" onClick={() => setOpen(true)} className="text-white"><Menu className="h-6 w-6" /></button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/50" />
          <aside className="absolute right-0 top-0 flex h-full w-64 flex-col bg-maroon-800 p-4" onClick={(e) => e.stopPropagation()}>
            <button aria-label="Close menu" onClick={() => setOpen(false)} className="mb-3 self-end text-white"><X className="h-6 w-6" /></button>
            {nav}
            <button onClick={logout} className="mt-4 flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-maroon-200"><LogOut className="h-4 w-4" /> Log out</button>
          </aside>
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 lg:py-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  );
}

function Brand({ name, compact }: { name: string; compact?: boolean }) {
  return (
    <div className={compact ? "flex items-center gap-2" : "mb-6 flex items-center gap-2 px-2 pt-2"}>
      <BarChart3 className="h-6 w-6 text-gold-400" />
      <div className="leading-tight">
        <div className="font-display text-lg font-semibold text-gold-300">Kasauti</div>
        <div className="max-w-[10rem] truncate text-xs text-maroon-200">{name}</div>
      </div>
    </div>
  );
}
