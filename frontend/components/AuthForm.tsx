"use client";
import { BarChart3 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import { ErrorBox, Field } from "./ui";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const { me, login } = useAuth();
  const { busy, error, run } = useAction();
  const [f, setF] = useState({ email: "", password: "", shop_name: "", phone: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  useEffect(() => {
    if (me) router.replace("/dashboard");
  }, [me, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await run(async () => {
      const body = mode === "signup" ? { ...f, phone: f.phone || null } : { email: f.email, password: f.password };
      const { access_token } = await api<{ access_token: string }>(`/auth/${mode}`, { body });
      await login(access_token);
      router.replace("/dashboard");
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-maroon-800 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center gap-2">
          <BarChart3 className="h-7 w-7 text-gold-500" />
          <span className="font-display text-2xl font-semibold text-maroon-800">Kasauti</span>
        </div>
        <h1 className="mb-1 text-lg font-semibold">{mode === "login" ? "Welcome back" : "Create your shop account"}</h1>
        <p className="mb-5 text-sm text-stone-500">{mode === "login" ? "Log in to manage rates, alerts and schemes." : "Daily rates, branded banners and customer alerts in one place."}</p>
        <form onSubmit={submit} className="space-y-3">
          {mode === "signup" && (
            <>
              <Field label="Shop name"><input className="input" required value={f.shop_name} onChange={set("shop_name")} placeholder="Raj Jewellers" /></Field>
              <Field label="Phone (optional)"><input className="input" inputMode="tel" value={f.phone} onChange={set("phone")} placeholder="98xxxxxx10" /></Field>
            </>
          )}
          <Field label="Email"><input className="input" type="email" required autoComplete="email" value={f.email} onChange={set("email")} /></Field>
          <Field label="Password" hint={mode === "signup" ? "At least 8 characters" : undefined}>
            <input className="input" type="password" required minLength={mode === "signup" ? 8 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={f.password} onChange={set("password")} />
          </Field>
          {error && <ErrorBox message={error} />}
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}</button>
        </form>
        <p className="mt-4 text-center text-sm text-stone-500">
          {mode === "login" ? (<>New here? <Link className="font-medium text-maroon-600 underline" href="/signup">Create an account</Link></>) : (<>Already registered? <Link className="font-medium text-maroon-600 underline" href="/login">Log in</Link></>)}
        </p>
      </div>
    </div>
  );
}
