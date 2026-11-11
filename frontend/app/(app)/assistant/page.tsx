"use client";
import { Bot, Check, Send, Square, Wrench, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ErrorBox, PageHeader } from "@/components/ui";
import { ApiError, api, streamChat } from "@/lib/api";
import { useApi } from "@/lib/hooks";

interface Pending { id: string; summary: string; state?: "confirmed" | "cancelled" | "error"; error?: string }
interface Msg { role: "user" | "assistant"; content: string; tools?: string[]; pending?: Pending[] }

const EXAMPLES = ["aaj gold ka rate kya hai?", "is mahine kiski payment pending hai?", "Why did silver move this week?", "Which customers are overdue?"];
const TOOL_LABEL: Record<string, string> = {
  get_price: "Checked price", get_price_movement: "Checked price history", list_pending_payments: "Looked up pending payments",
  customer_scheme_status: "Looked up customer", draft_reminder: "Drafted reminder", propose_record_payment: "Proposed payment entry",
};

export default function AssistantPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const earlier = useApi<{ id: string; summary: string }[]>("/agent/pending");

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs]);
  useEffect(() => () => abort.current?.abort(), []);

  const patchLast = (fn: (m: Msg) => Msg) => setMsgs((all) => all.map((m, i) => (i === all.length - 1 ? fn(m) : m)));

  const send = async (text: string) => {
    const t = text.trim();
    if (!t || busy) return;
    setError(null);
    setInput("");
    const history = [...msgs, { role: "user" as const, content: t }];
    setMsgs([...history, { role: "assistant", content: "" }]);
    setBusy(true);
    const ctl = new AbortController();
    abort.current = ctl;
    try {
      await streamChat(history.map((m) => ({ role: m.role, content: m.content })), (ev) => {
        if (ev.type === "text") patchLast((m) => ({ ...m, content: m.content + ev.delta }));
        else if (ev.type === "tool_call") patchLast((m) => ({ ...m, tools: [...(m.tools || []), ev.name] }));
        else if (ev.type === "pending_action") patchLast((m) => ({ ...m, pending: [...(m.pending || []), { id: ev.id, summary: ev.summary }] }));
        else if (ev.type === "error") setError(ev.message);
      }, ctl.signal);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError(e instanceof ApiError ? e.message : "Connection lost.");
    } finally {
      setBusy(false);
      abort.current = null;
      setMsgs((all) => all.filter((m, i) => !(i === all.length - 1 && m.role === "assistant" && !m.content && !m.tools?.length)));
    }
  };

  const resolve = async (msgIdx: number, id: string, action: "confirm" | "cancel") => {
    const set = (state: Pending["state"], err?: string) => setMsgs((all) => all.map((m, i) => (i !== msgIdx ? m : { ...m, pending: m.pending?.map((p) => (p.id === id ? { ...p, state, error: err } : p)) })));
    try {
      await api(`/agent/${action}/${id}`, { method: "POST" });
      set(action === "confirm" ? "confirmed" : "cancelled");
    } catch (e) {
      set("error", (e as Error).message);
    }
  };

  const resolveEarlier = async (id: string, action: "confirm" | "cancel") => {
    try { await api(`/agent/${action}/${id}`, { method: "POST" }); } catch (e) { setError((e as Error).message); }
    earlier.reload();
  };

  const knownIds = new Set(msgs.flatMap((m) => m.pending?.map((p) => p.id) || []));
  const waiting = (earlier.data || []).filter((p) => !knownIds.has(p.id));

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[420px] flex-col lg:h-[calc(100vh-4rem)]">
      <PageHeader title="AI Assistant" subtitle="Ask in Hindi, Hinglish or English. Numbers come from your data; changes need your confirmation." />
      {waiting.length > 0 && (
        <div className="mb-3 space-y-2">
          {waiting.map((p) => (
            <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
              <span>Waiting for your confirmation: {p.summary}</span>
              <span className="flex gap-2"><button className="btn-primary py-1" onClick={() => resolveEarlier(p.id, "confirm")}>Confirm</button><button className="btn-ghost py-1" onClick={() => resolveEarlier(p.id, "cancel")}>Cancel</button></span>
            </div>
          ))}
        </div>
      )}

      <div className="card flex-1 overflow-y-auto" aria-live="polite">
        {msgs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Bot className="mb-3 h-10 w-10 text-gold-500" />
            <p className="mb-4 text-sm text-stone-500">Try one of these:</p>
            <div className="flex flex-wrap justify-center gap-2">{EXAMPLES.map((e) => <button key={e} className="btn-ghost" onClick={() => send(e)}>{e}</button>)}</div>
          </div>
        ) : (
          <div className="space-y-4">
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-maroon-600 text-white" : "bg-stone-100 text-ink"}`}>
                  {m.tools && m.tools.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1.5">{m.tools.map((t, k) => <span key={k} className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-xs text-stone-600"><Wrench className="h-3 w-3" /> {TOOL_LABEL[t] || t}</span>)}</div>
                  )}
                  <div className="whitespace-pre-wrap">{m.content || (busy && i === msgs.length - 1 ? <span className="text-stone-400">Thinking...</span> : null)}</div>
                  {m.pending?.map((p) => (
                    <div key={p.id} className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-stone-800">
                      <div className="text-xs font-medium uppercase tracking-wide text-amber-800">Needs your confirmation</div>
                      <div className="my-1">{p.summary}</div>
                      {!p.state && <div className="mt-2 flex gap-2"><button className="btn-primary py-1" onClick={() => resolve(i, p.id, "confirm")}><Check className="h-4 w-4" /> Confirm</button><button className="btn-ghost py-1" onClick={() => resolve(i, p.id, "cancel")}><X className="h-4 w-4" /> Cancel</button></div>}
                      {p.state === "confirmed" && <div className="text-sm font-medium text-emerald-700">Done. Recorded.</div>}
                      {p.state === "cancelled" && <div className="text-sm text-stone-500">Cancelled. Nothing was changed.</div>}
                      {p.state === "error" && <div className="text-sm text-red-700">{p.error}</div>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <div ref={end} />
          </div>
        )}
      </div>

      {error && <div className="mt-3"><ErrorBox message={error} /></div>}
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input className="input" placeholder="Type your question..." value={input} onChange={(e) => setInput(e.target.value)} maxLength={2000} aria-label="Message" />
        {busy ? <button type="button" className="btn-ghost" onClick={() => abort.current?.abort()}><Square className="h-4 w-4" /> Stop</button> : <button className="btn-primary" disabled={!input.trim()}><Send className="h-4 w-4" /> Send</button>}
      </form>
      <p className="mt-2 text-xs text-stone-400">AI can make mistakes. Check important figures on the Dashboard. Rates are indicative, not investment advice.</p>
    </div>
  );
}
