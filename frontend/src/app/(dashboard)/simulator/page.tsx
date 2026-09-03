"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Target, Sparkles, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/Sidebar";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { fmtINR, fmtNum } from "@/lib/utils";
import type { SimulateResult } from "@/lib/types";

export default function SimulatorPage() {
  const { profile } = useAuth();
  const [price, setPrice] = useState(0);
  const [mkt, setMkt] = useState(0);
  const [inv, setInv] = useState(0);
  const [supplier, setSupplier] = useState(false);
  const [result, setResult] = useState<SimulateResult | null>(null);

  const run = useCallback(() => {
    api.simulate(profile?.region ?? null, { priceChangePct: price, marketingSpendPct: mkt, inventoryInvestPct: inv, supplierSwitch: supplier })
      .then(setResult).catch(() => {});
  }, [price, mkt, inv, supplier, profile]);

  useEffect(() => { run(); }, [run]);

  const rows: Array<{ label: string; key: keyof SimulateResult["result"]; base: number; fmt: (v: number) => string }> = result
    ? [
        { label: "Revenue", key: "revenue", base: result.base.revenue, fmt: fmtINR },
        { label: "Profit", key: "profit", base: result.base.profit, fmt: fmtINR },
        { label: "Orders", key: "orders", base: result.base.orders, fmt: fmtNum },
        { label: "Inventory Health", key: "invHealth", base: result.base.invHealth, fmt: (v) => `${Math.round(v)}%` },
        { label: "Customer Satisfaction", key: "csat", base: result.base.csat, fmt: (v) => `${Math.round(v)}/100` },
      ]
    : [];

  return (
    <div>
      <PageHeader title="Decision Simulator" sub="Test a scenario before you commit to it" />
      <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 1.15fr" }}>
        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-4"><Target size={16} className="text-[var(--purple)]" /> Scenario levers</div>

          <div className="mb-5">
            <div className="flex justify-between items-baseline mb-2.5">
              <span className="text-[12.5px] font-semibold">Price change</span>
              <span className="text-[13px] font-bold font-mono-tab text-[var(--cyan)]">{price >= 0 ? "+" : ""}{price}%</span>
            </div>
            <Slider value={[price]} min={-15} max={15} step={1} onValueChange={([v]) => setPrice(v)} />
          </div>

          <div className="mb-5">
            <div className="flex justify-between items-baseline mb-2.5">
              <span className="text-[12.5px] font-semibold">Marketing spend change</span>
              <span className="text-[13px] font-bold font-mono-tab text-[var(--cyan)]">{mkt >= 0 ? "+" : ""}{mkt}%</span>
            </div>
            <Slider value={[mkt]} min={-50} max={100} step={5} onValueChange={([v]) => setMkt(v)} />
          </div>

          <div className="mb-5">
            <div className="flex justify-between items-baseline mb-2.5">
              <span className="text-[12.5px] font-semibold">Inventory investment</span>
              <span className="text-[13px] font-bold font-mono-tab text-[var(--cyan)]">+{inv}%</span>
            </div>
            <Slider value={[inv]} min={0} max={100} step={5} onValueChange={([v]) => setInv(v)} />
          </div>

          <div className="mb-1">
            <div className="flex justify-between items-baseline mb-2.5">
              <span className="text-[12.5px] font-semibold">Switch to backup supplier</span>
              <span className="text-[13px] font-bold font-mono-tab text-[var(--cyan)]">{supplier ? "On" : "Off"}</span>
            </div>
            <Button className="w-full justify-center" onClick={() => setSupplier((s) => !s)}>Toggle supplier switch</Button>
          </div>

          <div className="mt-4 pt-3.5 border-t border-white/[0.09] text-[11px] text-[var(--text-tertiary)]">
            Elasticity coefficients, margin curves, and risk formulas are fixed and transparent — no model inference in this engine.
          </div>
        </div>

        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-4"><Sparkles size={16} className="text-[var(--purple)]" /> Projected impact (next 7 days)</div>
          {rows.map((r) => {
            const after = result!.result[r.key];
            const up = after >= r.base;
            return (
              <div key={r.key} className="flex items-center justify-between py-2.5 border-b border-white/[0.09] last:border-none">
                <div className="text-[12.5px] text-[var(--text-secondary)]">{r.label}</div>
                <div className="flex items-center gap-2.5 font-mono-tab text-[13px]">
                  <span className="text-[var(--text-tertiary)]">{r.fmt(r.base)}</span>
                  <ArrowRight size={12} className="text-[var(--text-tertiary)]" />
                  <motion.span key={after} initial={{ opacity: 0.3 }} animate={{ opacity: 1 }} className="font-bold" style={{ color: up ? "var(--green)" : "var(--red)" }}>
                    {r.fmt(after)}
                  </motion.span>
                </div>
              </div>
            );
          })}
          {result && (
            <div className="flex items-center justify-between py-2.5">
              <div className="text-[12.5px] text-[var(--text-secondary)]">Risk Score</div>
              <span className="font-mono-tab text-[13px] font-bold" style={{ color: result.result.risk < 40 ? "var(--green)" : result.result.risk < 65 ? "var(--amber)" : "var(--red)" }}>
                {result.result.risk}/100
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
