"use client";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { AuthCard } from "./AuthCard";
import { ErrorBox, Field } from "./ui";

export function ForgotPasswordForm() {
  const { busy, error, run } = useAction();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const ok = await run(async () => {
      await api("/auth/forgot-password", { body: { email } });
      return true;
    });
    if (ok) setSent(true);
  };

  return (
    <AuthCard title="Forgot your password?" subtitle="Enter your account email and we will send you a link to choose a new password.">
      {sent ? (
        <div className="space-y-4">
          <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            If an account exists for <strong>{email}</strong>, a reset link is on its way. It is valid for 30 minutes.
          </div>
          <Link className="btn-primary w-full" href="/login">Back to login</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <Field label="Email">
            <input className="input" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          {error && <ErrorBox message={error} />}
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait..." : "Send reset link"}</button>
          <p className="text-center text-sm text-stone-500">
            Remembered it? <Link className="font-medium text-maroon-600 underline" href="/login">Log in</Link>
          </p>
        </form>
      )}
    </AuthCard>
  );
}