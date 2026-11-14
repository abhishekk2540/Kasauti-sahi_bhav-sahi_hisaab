"use client";
import { BarChart3 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import { ErrorBox, Field } from "./ui";

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{7,128}$/;

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const { me, login } = useAuth();
  const { busy, error, run } = useAction();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", confirmPassword: "" });
  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  useEffect(() => {
    if (me) router.replace("/dashboard");
  }, [me, router]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    await run(async () => {
      if (mode === "signup") {
        if (!passwordPattern.test(form.password)) {
          throw new Error("Password needs 7+ characters, uppercase, lowercase, a number, and a special character.");
        }
        if (form.password !== form.confirmPassword) throw new Error("Passwords do not match.");
      }
      const body = mode === "signup"
        ? { name: form.name, email: form.email, phone: form.phone || null, password: form.password, confirm_password: form.confirmPassword }
        : { email: form.email, password: form.password };
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
        <h1 className="mb-1 text-lg font-semibold">{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="mb-5 text-sm text-stone-500">{mode === "login" ? "Log in to manage rates, alerts and schemes." : "Create your Kasauti account to manage your shop."}</p>
        <form onSubmit={submit} className="space-y-3">
          {mode === "signup" && (
            <>
              <Field label="Name"><input className="input" required maxLength={120} value={form.name} onChange={set("name")} /></Field>
              <Field label="Phone number"><input className="input" required inputMode="tel" pattern="[0-9+\- ]{7,20}" title="7-20 digits, may start with +" maxLength={20} value={form.phone} onChange={set("phone")} /></Field>
            </>
          )}
          <Field label="Email"><input className="input" type="email" required autoComplete="email" value={form.email} onChange={set("email")} /></Field>
          <Field label="Password" hint={mode === "signup" ? "7+ chars, upper/lowercase, number and special character" : undefined}>
            <input className="input" type="password" required minLength={mode === "signup" ? 7 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={form.password} onChange={set("password")} />
          </Field>
          {mode === "signup" && (
            <Field label="Confirm password">
              <input className="input" type="password" required minLength={7} autoComplete="new-password" value={form.confirmPassword} onChange={set("confirmPassword")} />
            </Field>
          )}
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
