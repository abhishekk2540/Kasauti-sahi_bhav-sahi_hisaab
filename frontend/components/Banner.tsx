"use client";
import { Download, Share2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { fetchBlob } from "@/lib/api";
import { ErrorBox, Spinner } from "./ui";

export function Banner({ refreshKey }: { refreshKey: number }) {
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [canShare, setCanShare] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setBlob(await fetchBlob("/banner.png"));
    } catch (e) {
      setBlob(null);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, refreshKey]);
  useEffect(() => {
    if (!blob) return setUrl(null);
    const u = URL.createObjectURL(blob);
    setUrl(u);
    setCanShare(!!navigator.canShare?.({ files: [new File([blob], "rates.png", { type: "image/png" })] }));
    return () => URL.revokeObjectURL(u);
  }, [blob]);

  const fileName = `rates-${new Date().toISOString().slice(0, 10)}.png`;
  const share = async () => {
    if (!blob) return;
    try {
      await navigator.share({ files: [new File([blob], fileName, { type: "image/png" })], text: "Aaj ka bhav" });
    } catch {
      /* user cancelled */
    }
  };

  if (loading) return <Spinner label="Generating banner..." />;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  return (
    <div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {url && <img src={url} alt="Today's rate banner" className="mx-auto w-full max-w-sm rounded-xl border border-stone-200 shadow" />}
      <div className="mt-3 flex flex-wrap justify-center gap-2">
        {canShare && <button className="btn-primary" onClick={share}><Share2 className="h-4 w-4" /> Share (WhatsApp etc.)</button>}
        {url && <a className={canShare ? "btn-ghost" : "btn-primary"} href={url} download={fileName}><Download className="h-4 w-4" /> Download</a>}
      </div>
      {!canShare && <p className="mt-2 text-center text-xs text-stone-400">On a phone, a Share button appears so you can send it to WhatsApp in one tap.</p>}
    </div>
  );
}
