import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/playfair-display";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = { title: "Kasauti: jeweller toolkit", description: "Daily rates, customer alerts, savings schemes and an AI assistant for jewellers." };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#5a1825" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
