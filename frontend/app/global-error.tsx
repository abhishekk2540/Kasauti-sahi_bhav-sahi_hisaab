"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/ErrorState";
import "./globals.css";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Unhandled application error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <ErrorState kind="server" message="Kasauti could not start correctly. Try again or return to the dashboard." onRetry={reset} />
      </body>
    </html>
  );
}
