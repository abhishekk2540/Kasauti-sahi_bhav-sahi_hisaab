"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { PASSWORD_HINT, PASSWORD_RULE_MESSAGE, passwordPattern } from "@/lib/password";
import { AuthCard } from "./AuthCard";
import { PasswordInput } from "./PasswordInput";
import { ErrorBox, Field } from "./ui";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") || "";
  const { busy, error, run } = useAction();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <AuthCard title="Reset link missing" subtitle="This page needs the link from your reset message.">
        <Link className="btn-primary w-full" href="/forgot-password">Request a new link</Link>
      </AuthCard>
    );
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const ok = await run(async () => {
      if (!passwordPattern.test(password)) throw new Error(PASSWORD_RULE_MESSAGE);
      if (password !== confirm) throw new Error("Passwords do not match.");
      await api("/auth/reset-password", { body: { token, password, confirm_password: confirm } });
      return true;
    });
    if (ok) setDone(true);
  };

  return (
    <AuthCard title="Choose a new password" subtitle={done ? undefined : "Pick a strong password you have not used before."}>
      {done ? (
        <div className="space-y-4">
          <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            Your password has been updated.
          </div>
          <Link className="btn-primary w-full" href="/login">Go to login</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <Field label="New password" hint={PASSWORD_HINT}>
            <PasswordInput required minLength={7} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label="Confirm new password">
            <PasswordInput required minLength={7} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </Field>
          {error && <ErrorBox message={error} />}
          {error && /invalid or has expired/i.test(error) && (
            <Link className="block text-center text-sm font-medium text-maroon-600 underline" href="/forgot-password">Request a new link</Link>
          )}
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait..." : "Update password"}</button>
        </form>
      )}
    </AuthCard>
  );
}