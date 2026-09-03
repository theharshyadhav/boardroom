"use client";
import { useEffect, useState, useCallback } from "react";
import { Sparkles, Send, Check } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "./ui/button";

export function ExecutiveSummaryCard() {
  const { persona } = useAuth();
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api
      .summary(persona)
      .then((r) => setText(r.text))
      .catch(() => setText("Couldn't reach the BoardMind API for a narrative right now."))
      .finally(() => setLoading(false));
  }, [persona]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between mb-3.5">
        <div className="text-[14.5px] font-bold flex items-center gap-2">
          <Sparkles size={16} className="text-[var(--purple)]" /> Executive Summary
        </div>
        <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
          <Send size={12} /> Regenerate
        </Button>
      </div>
      {loading ? (
        <div className="space-y-2">
          <div className="skeleton h-3.5 w-full" />
          <div className="skeleton h-3.5 w-[92%]" />
          <div className="skeleton h-3.5 w-[76%]" />
        </div>
      ) : (
        <div className="text-[13px] leading-relaxed text-[var(--text-secondary)]">{text}</div>
      )}
      <div className="mt-3.5 pt-3.5 border-t border-white/[0.09] text-[11px] text-[var(--text-tertiary)] flex items-center gap-1.5">
        <Check size={12} /> Narrated live by Claude from pre-computed figures — no numbers are model-generated.
      </div>
    </div>
  );
}
