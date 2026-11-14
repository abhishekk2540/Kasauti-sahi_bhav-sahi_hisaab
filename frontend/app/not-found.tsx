import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">Page not found</h1>
      <p className="text-stone-600">The page you requested does not exist.</p>
      <Link href="/dashboard" className="btn-primary">Go to dashboard</Link>
    </main>
  );
}
