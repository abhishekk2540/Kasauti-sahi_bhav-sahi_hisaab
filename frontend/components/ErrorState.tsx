"use client";

import { AlertTriangle, Home, RefreshCw, ServerCrash, WifiOff } from "lucide-react";
import Link from "next/link";

export type ErrorKind = "server" | "api" | "network";

const ERROR_COPY: Record<ErrorKind, { title: string; description: string }> = {
  server: {
    title: "Something went wrong",
    description: "Kasauti could not load this page. Please try again.",
  },
  api: {
    title: "Service error",
    description: "The server returned an unexpected response. Please retry in a moment.",
  },
  network: {
    title: "Connection problem",
    description: "Kasauti cannot reach the server. Check your internet connection and try again.",
  },
};

function iconFor(kind: ErrorKind) {
  if (kind === "network") return WifiOff;
  if (kind === "api") return ServerCrash;
  return AlertTriangle;
}

export function ErrorState({
  kind,
  message,
  onRetry,
}: {
  kind: ErrorKind;
  message?: string;
  onRetry?: () => void;
}) {
  const copy = ERROR_COPY[kind];
  const Icon = iconFor(kind);
  return (
    <div role="alert" className="flex min-h-[40vh] items-center justify-center p-6">
      <div className="card w-full max-w-lg text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-red-700">
          <Icon className="h-7 w-7" />
        </div>
        <h1 className="font-display text-2xl font-semibold text-maroon-800">{copy.title}</h1>
        <p className="mx-auto mt-2 max-w-md text-sm text-stone-600">{message || copy.description}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {onRetry && (
            <button className="btn-primary" onClick={onRetry}>
              <RefreshCw className="h-4 w-4" /> Try again
            </button>
          )}
          <Link className="btn-ghost" href="/dashboard">
            <Home className="h-4 w-4" /> Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
