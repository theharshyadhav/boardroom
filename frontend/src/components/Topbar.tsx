"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DataSource } from "@/lib/types";
import { useAuth } from "@/lib/auth";

const LABELS: Record<string, string> = { sales: "Sales", inventory: "Inventory", marketing: "Marketing" };

export function FreshnessTicker() {
  const [sources, setSources] = useState<DataSource[]>([]);

  useEffect(() => {
    api.freshness().then(setSources).catch(() => setSources([]));
  }, []);

  const shown = sources.filter((s) => ["sales", "inventory", "marketing"].includes(s.id));
  if (shown.length === 0) return null;

  return (
    <div className="glass flex items-center gap-3.5 px-3.5 py-2 rounded-full">
      {shown.map((s) => {
        const stale = s.freshnessMins > s.cadenceMins * 0.8;
        return (
          <div key={s.id} className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background: stale ? "var(--amber)" : "var(--green)",
                boxShadow: `0 0 8px ${stale ? "var(--amber)" : "var(--green)"}`,
              }}
            />
            {LABELS[s.id]} · {s.freshnessLabel}
          </div>
        );
      })}
    </div>
  );
}

export function PersonaSelect() {
  const { persona, setPersona } = useAuth();
  return (
    <select
      value={persona}
      onChange={(e) => setPersona(e.target.value)}
      className="font-mono-tab text-[11.5px] font-semibold px-3 py-2 rounded-full bg-white/[0.03] border border-white/[0.09] text-[var(--text-primary)]"
    >
      <option value="ceo">CEO view</option>
      <option value="finance">Finance view</option>
      <option value="marketing">Marketing view</option>
      <option value="regional">Regional view</option>
    </select>
  );
}
