"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/ErrorState";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Unhandled page error:", error);
  }, [error]);

  return <ErrorState kind="server" message="This page encountered an unexpected error. Try again or return to the dashboard." onRetry={reset} />;
}
