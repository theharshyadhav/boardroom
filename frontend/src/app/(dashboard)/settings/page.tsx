"use client";
import { useEffect, useState } from "react";
import { Target, Megaphone, Sparkles, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/Sidebar";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { profile, roleKey, persona, login } = useAuth();
  const [roles, setRoles] = useState<Array<{ key: string; title: string }>>([]);
  const [resetting, setResetting] = useState(false);

  useEffect(() => { api.listRoles().then(setRoles).catch(() => {}); }, []);

  return (
    <div>
      <PageHeader title="Settings" sub="Access, personas, and system architecture" />

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-3.5"><Target size={16} className="text-[var(--purple)]" /> Access &amp; role</div>
          <div className="text-[12.5px] text-[var(--text-secondary)] leading-loose">
            Signed in as <b className="text-white">{profile?.name}</b>, {profile?.title}.<br />
            Region scope: <b>{profile?.region || "All regions"}</b><br />
            Financial detail: <b>{profile?.hideFinance ? "Restricted" : "Full access"}</b>
          </div>
          <div className="mt-3.5 flex flex-wrap gap-1.5">
            {roles.map((r) => (
              <Button key={r.key} variant={r.key === roleKey ? "primary" : "ghost"} size="sm" onClick={() => login(r.key)}>
                {r.title}
              </Button>
            ))}
          </div>
        </div>

        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-3.5"><Megaphone size={16} className="text-[var(--purple)]" /> Narrative persona</div>
          <div className="text-[12.5px] text-[var(--text-secondary)] leading-relaxed mb-3">
            Controls tone and depth of AI-generated narrative — independent from your data access above.
          </div>
          <div className="text-[12px] text-[var(--text-tertiary)]">
            Currently: <b className="font-mono-tab text-[var(--cyan)]">{persona}</b> — change it from the top bar on the Dashboard.
          </div>
        </div>
      </div>

      <div className="glass p-5 mb-4">
        <div className="text-[14.5px] font-bold flex items-center gap-2 mb-3.5"><Sparkles size={16} className="text-[var(--purple)]" /> Architecture — deterministic vs. LLM</div>
        <div className="text-[12px] text-[var(--text-secondary)] leading-loose font-mono-tab">
          Data Sources → DuckDB Harmonization → Semantic KPI Layer → Material Change Detection (statistics) → Driver Analysis (scikit-learn) → Evidence Graph (NetworkX) → Confidence Engine → Recommendation Engine → Simulation Engine
          <span className="text-[var(--green)] font-bold"> — all pure Python, zero model calls</span><br />
          → LLM Narrative <span className="text-[var(--purple)] font-bold">— the only stage that calls an LLM, and only to phrase numbers already computed above</span> → Next.js Dashboard
        </div>
      </div>

      <div className="glass p-5">
        <div className="text-[14.5px] font-bold flex items-center gap-2 mb-2"><XCircle size={16} className="text-[var(--purple)]" /> Reset feedback history</div>
        <div className="text-[12px] text-[var(--text-tertiary)] mb-2.5">Clears the SQLite-backed accept / reject / modify history used by the recommendation feedback loop.</div>
        <Button
          variant="dangerOutline" size="sm" disabled={resetting}
          onClick={async () => { setResetting(true); await api.resetFeedback(); setResetting(false); }}
        >
          Clear stored feedback
        </Button>
      </div>
    </div>
  );
}
