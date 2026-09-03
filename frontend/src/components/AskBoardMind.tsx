"use client";
import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";

interface Msg { role: "user" | "ai"; text: string; pending?: boolean }

export function AskBoardMind() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }); }, [msgs]);

  async function send() {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "ai", text: "", pending: true }]);
    setBusy(true);
    try {
      const res = await api.ask(q);
      setMsgs((m) => m.map((x, i) => (i === m.length - 1 ? { role: "ai", text: res.answer } : x)));
    } catch {
      setMsgs((m) => m.map((x, i) => (i === m.length - 1 ? { role: "ai", text: "Couldn't reach the BoardMind API." } : x)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass p-5">
      <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><Send size={16} className="text-[var(--purple)]" /> Ask BoardMind</div>
      <div className="text-[11.5px] text-[var(--text-tertiary)] mb-3.5">
        Answers are grounded strictly in the same pre-computed digest shown above — if the data can&apos;t answer it, BoardMind will say so.
      </div>
      <div ref={scrollRef} className="max-h-[340px] overflow-y-auto flex flex-col gap-3 pr-1">
        {msgs.map((m, i) => (
          <div
            key={i}
            className={`text-[12.5px] leading-relaxed px-3.5 py-2.5 rounded-2xl max-w-[88%] ${
              m.role === "user" ? "self-end text-white rounded-br-[4px]" : "self-start bg-white/[0.05] border border-white/[0.09] rounded-bl-[4px]"
            }`}
            style={m.role === "user" ? { background: "var(--grad-brand)" } : undefined}
          >
            {m.pending ? (
              <span className="inline-flex gap-1 items-center py-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)] animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            ) : m.text}
          </div>
        ))}
      </div>
      <div className="flex gap-2 mt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="e.g. Why did South India underperform this week?"
          className="flex-1 px-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.09] text-[var(--text-primary)] text-[12.5px]"
        />
        <Button variant="primary" size="sm" onClick={send} disabled={busy}><Send size={13} /></Button>
      </div>
    </div>
  );
}
