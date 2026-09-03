"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Boxes, Crown, Wallet, Megaphone, MapPin } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const ICONS: Record<string, React.ElementType> = { ceo: Crown, finance: Wallet, marketing: Megaphone, regional: MapPin };
const DESCS: Record<string, string> = {
  ceo: "Full access across every region and function",
  finance: "Full financial detail, marketing shown at a summary level",
  marketing: "Campaign & sentiment focus, financial detail restricted",
  regional: "South India only, across every module",
};

export default function LoginPage() {
  const { login, roleKey } = useAuth();
  const [roles, setRoles] = useState<Array<{ key: string; name: string; title: string }>>([]);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    api.listRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  async function handleLogin(key: string) {
    setPending(key);
    try {
      await login(key);
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
        className="glass w-[420px] max-w-full p-9 text-center"
      >
        <div className="w-[52px] h-[52px] rounded-2xl mx-auto mb-4.5 flex items-center justify-center shadow-[0_8px_30px_rgba(139,92,246,0.5)]" style={{ background: "var(--grad-brand)" }}>
          <Boxes size={26} color="white" />
        </div>
        <div className="text-[19px] font-extrabold tracking-tight">BoardMind</div>
        <div className="text-[12px] text-[var(--text-tertiary)] mb-5.5">The AI Executive Decision Intelligence Platform</div>

        <div className="text-[11px] text-[var(--text-tertiary)] text-left mb-2.5 uppercase tracking-wide">Sign in as</div>
        <div className="flex flex-col gap-2">
          {roles.length === 0 && (
            <div className="text-[12px] text-[var(--text-tertiary)] py-4">
              Couldn&apos;t reach the BoardMind API — is the backend running on {process.env.NEXT_PUBLIC_API_URL || "https://boardroom-api-25xh.onrender.com"}?
            </div>
          )}
          {roles.map((r) => {
            const Icon = ICONS[r.key] || Crown;
            return (
              <button
                key={r.key}
                onClick={() => handleLogin(r.key)}
                disabled={!!pending}
                className="flex items-center gap-3 w-full px-3.5 py-3 rounded-[13px] bg-white/[0.03] border border-white/[0.09] hover:bg-white/[0.08] hover:translate-x-0.5 transition-all text-left disabled:opacity-50"
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--grad-brand-soft)" }}>
                  <Icon size={16} className="text-[var(--cyan)]" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold">{r.name} · {r.title}</div>
                  <div className="text-[10.5px] text-[var(--text-tertiary)]">{DESCS[r.key]}</div>
                </div>
              </button>
            );
          })}
        </div>
        <div className="text-[10px] text-[var(--text-tertiary)] mt-3.5">Demo access · role-based views, no password required</div>
      </motion.div>
    </div>
  );
}
