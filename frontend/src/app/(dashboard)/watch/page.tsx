"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Radar, Power, Upload, CalendarClock, RefreshCw, Bell, Check } from "lucide-react";
import { api } from "@/lib/api";
import type { WatchStatus, Alert as AlertT } from "@/lib/api";
import { PageHeader } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const SEVERITY_TONE: Record<string, "low" | "medium" | "high" | "critical" | "neutral"> = {
  info: "low", medium: "medium", high: "high", critical: "critical",
};

export default function WatchPage() {
  const [status, setStatus] = useState<WatchStatus | null>(null);
  const [alerts, setAlerts] = useState<AlertT[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const refresh = () => {
    api.watchStatus().then(setStatus).catch(() => {});
    api.alerts().then(setAlerts).catch(() => {});
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  async function toggle() {
    if (!status) return;
    setBusy("toggle");
    await api.toggleWatch(!status.enabled).catch(() => {});
    refresh();
    setBusy(null);
  }

  async function fire(fn: () => Promise<{ workflow_id: string }>, label: string) {
    setBusy(label);
    try {
      const res = await fn();
      setLastAction(`${label} \u2192 workflow ${res.workflow_id.slice(0, 8)}\u2026 dispatched`);
    } catch (e) {
      setLastAction(e instanceof Error ? e.message : `${label} failed`);
    } finally {
      setBusy(null);
      refresh();
    }
  }

  async function ack(id: string) {
    await api.ackAlert(id).catch(() => {});
    refresh();
  }

  return (
    <div>
      <PageHeader
        title="Executive Watch Mode"
        sub="Continuous autonomous monitoring \u2014 no manual Generate click required"
        right={
          <Button variant={status?.enabled ? "primary" : "default"} onClick={toggle} disabled={busy === "toggle"}>
            <Power size={14} /> {status?.enabled ? "Watch mode: ON" : "Watch mode: OFF"}
          </Button>
        }
      />

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
        <div className="glass px-4 py-3.5">
          <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">Status</div>
          <div className="text-[15px] font-bold flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${status?.enabled ? "bg-emerald-400" : "bg-white/20"}`} />
            {status?.enabled ? "Live" : "Paused"}
          </div>
        </div>
        <div className="glass px-4 py-3.5">
          <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">Pub/Sub</div>
          <div className="text-[15px] font-bold">{status?.pubsub_live ? "Live (Cloud Pub/Sub)" : "Local fallback"}</div>
        </div>
        <div className="glass px-4 py-3.5">
          <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">Last tick</div>
          <div className="text-[13px] font-bold font-mono-tab">{status?.last_tick_job ?? "\u2014"}</div>
        </div>
        <div className="glass px-4 py-3.5">
          <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">At</div>
          <div className="text-[12px] font-mono-tab">{status?.last_tick_at ? new Date(status.last_tick_at).toLocaleTimeString() : "\u2014"}</div>
        </div>
      </div>

      <div className="glass p-5 mb-4">
        <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><Radar size={16} className="text-[var(--purple)]" /> Manual triggers</div>
        <div className="text-[11.5px] text-[var(--text-tertiary)] mb-3.5">
          In production these fire automatically \u2014 Cloud Scheduler cron jobs and your document pipeline. Trigger them here to see the mesh react live.
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Button onClick={() => fire(() => api.triggerReportUploaded("q3-financials.pdf"), "Document uploaded")} disabled={!!busy}>
            <Upload size={13} /> Simulate document upload
          </Button>
          <Button onClick={() => fire(() => api.triggerScheduledTick("health-check"), "Health check tick")} disabled={!!busy}>
            <RefreshCw size={13} /> Run health-check tick
          </Button>
          <Button onClick={() => fire(() => api.triggerScheduledTick("daily-brief"), "Daily brief tick")} disabled={!!busy}>
            <CalendarClock size={13} /> Run daily CEO brief
          </Button>
        </div>
        {lastAction && <div className="text-[11.5px] text-[var(--text-tertiary)] mt-3">{lastAction}</div>}
      </div>

      <div className="glass p-5">
        <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><Bell size={16} className="text-[var(--purple)]" /> Enterprise alerts / notification center</div>
        <div className="text-[11.5px] text-[var(--text-tertiary)] mb-3.5">Raised by any agent \u2014 unacknowledged alerts persist across restarts (Firestore)</div>
        <div className="flex flex-col gap-2">
          {alerts.length === 0 && <div className="text-[12px] text-[var(--text-tertiary)]">No alerts yet.</div>}
          {alerts.map((a) => (
            <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-start gap-3 px-3.5 py-3 rounded-lg bg-white/[0.02] border border-white/[0.09]">
              <Badge tone={SEVERITY_TONE[a.severity] ?? "neutral"}>{a.severity}</Badge>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-semibold">{a.title}</div>
                <div className="text-[11.5px] text-[var(--text-secondary)] mt-0.5 line-clamp-2">{a.body}</div>
                <div className="text-[10px] text-[var(--text-tertiary)] mt-1">{a.agent} \u00b7 {new Date(a.created_at).toLocaleString()}</div>
              </div>
              {!a.acknowledged && (
                <Button size="sm" variant="ghost" onClick={() => ack(a.id)}><Check size={12} /> Ack</Button>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
