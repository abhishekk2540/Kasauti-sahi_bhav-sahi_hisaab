export const inr = (n: number | null | undefined, digits = 0) =>
  n == null ? "-" : "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const shortDate = (iso: string) =>
  new Date(iso.length <= 10 ? iso + "T00:00:00" : iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export const longDate = (iso: string) =>
  new Date(iso.length <= 10 ? iso + "T00:00:00" : iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export const pct = (n: number | null | undefined) => (n == null ? "-" : `${n > 0 ? "" : ""}${n.toFixed(1)}%`);
