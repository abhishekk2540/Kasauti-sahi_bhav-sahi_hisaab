"use client";
import { Copy, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ErrorBox, Field, PageHeader } from "@/components/ui";
import { api, fetchBlob } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";

export default function SettingsPage() {
  const { me, refresh, logout } = useAuth();
  const [shop, setShop] = useState(me?.shop_name ?? "");
  const [phone, setPhone] = useState(me?.phone ?? "");
  const [saved, setSaved] = useState(false);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const prof = useAction();
  const logo = useAction();

  useEffect(() => {
    let url: string | null = null;
    let live = true;
    if (me?.has_logo) fetchBlob("/me/logo").then((b) => { if (live) { url = URL.createObjectURL(b); setLogoUrl(url); } }).catch(() => {});
    else setLogoUrl(null);
    return () => { live = false; if (url) URL.revokeObjectURL(url); };
  }, [me?.has_logo, me?.id]);

  if (!me) return null;

  const saveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    prof.run(async () => { await api("/me", { method: "PATCH", body: { shop_name: shop, phone: phone || null } }); await refresh(); setSaved(true); setTimeout(() => setSaved(false), 2500); });
  };
  const upload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) return logo.setError("Logo must be under 2 MB.");
    logo.run(async () => { const fd = new FormData(); fd.append("file", f); await api("/me/logo", { method: "PUT", form: fd }); await refresh(); });
    e.target.value = "";
  };

  return (
    <>
      <PageHeader title="Settings" subtitle="Your shop details appear on the daily banner and customer messages" />
      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={saveProfile} className="card space-y-3">
          <h2 className="font-display text-lg font-semibold text-maroon-800">Shop profile</h2>
          <Field label="Shop name"><input className="input" required maxLength={120} value={shop} onChange={(e) => setShop(e.target.value)} /></Field>
          <Field label="Phone (shown to customers)"><input className="input" inputMode="tel" maxLength={20} value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
          <Field label="Email"><input className="input bg-stone-50" value={me.email} disabled /></Field>
          {prof.error && <ErrorBox message={prof.error} />}
          <div className="flex items-center gap-3"><button className="btn-primary" disabled={prof.busy}>{prof.busy ? "Saving..." : "Save"}</button>{saved && <span className="text-sm text-emerald-700">Saved</span>}</div>
        </form>

        <div className="card">
          <h2 className="mb-3 font-display text-lg font-semibold text-maroon-800">Shop logo</h2>
          <div className="mb-3 flex h-32 items-center justify-center rounded-lg border border-dashed border-stone-300 bg-stone-50">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {logoUrl ? <img src={logoUrl} alt="Shop logo" className="max-h-28 max-w-[80%] object-contain" /> : <span className="text-sm text-stone-400">No logo yet</span>}
          </div>
          <input ref={file} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={upload} />
          <button className="btn-ghost" onClick={() => file.current?.click()} disabled={logo.busy}><Upload className="h-4 w-4" /> {logo.busy ? "Uploading..." : me.has_logo ? "Replace logo" : "Upload logo"}</button>
          <p className="mt-2 text-xs text-stone-400">PNG, JPG or WebP, up to 2 MB. A square logo with a transparent background looks best on the banner.</p>
          {logo.error && <div className="mt-2"><ErrorBox message={logo.error} /></div>}
        </div>

        <div className="card lg:col-span-2">
          <h2 className="mb-1 font-display text-lg font-semibold text-maroon-800">Telegram alerts for you</h2>
          {me.telegram_linked ? <p className="text-sm text-emerald-700">Linked. Your own alerts will arrive on Telegram.</p> : me.telegram_link ? (
            <>
              <p className="mb-3 text-sm text-stone-600">Open this link in Telegram and press Start to receive your alerts there.</p>
              <div className="flex flex-wrap gap-2"><a className="btn-primary" href={me.telegram_link} target="_blank" rel="noreferrer">Open Telegram</a>
                <button className="btn-ghost" onClick={() => navigator.clipboard.writeText(me.telegram_link!)}><Copy className="h-4 w-4" /> Copy link</button>
                <button className="btn-ghost" onClick={refresh}>I have pressed Start</button></div>
            </>
          ) : <p className="text-sm text-stone-500">Telegram is not set up on the server yet (the backend needs TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_USERNAME).</p>}
        </div>
      </div>
      <button className="btn-danger mt-6" onClick={logout}>Log out</button>
    </>
  );
}
