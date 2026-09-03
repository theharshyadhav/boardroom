"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { LayoutDashboard, Lightbulb, Search, Users, SlidersHorizontal, Activity, Settings, ArrowLeftRight, Boxes, Bot, Radar, ActivitySquare } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/evidence", label: "Evidence", icon: Search },
  { href: "/boardroom", label: "Boardroom", icon: Users },
  { href: "/simulator", label: "Simulator", icon: SlidersHorizontal },
  { href: "/agents", label: "Agent Registry", icon: Bot },
  { href: "/watch", label: "Executive Watch", icon: Radar },
  { href: "/observability", label: "Observability", icon: ActivitySquare },
  { href: "/telemetry", label: "Telemetry", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { profile, logout } = useAuth();

  return (
    <div className="sticky top-0 h-screen w-[248px] shrink-0 flex flex-col gap-1 py-5.5 px-3.5 bg-gradient-to-b from-white/[0.035] to-white/[0.015] border-r border-white/[0.09] max-md:hidden">
      <div className="flex items-center gap-2.5 px-2.5 pb-5.5 pt-2">
        <div className="w-[30px] h-[30px] rounded-[9px] flex items-center justify-center shrink-0 shadow-[0_4px_16px_rgba(139,92,246,0.45)]" style={{ background: "var(--grad-brand)" }}>
          <Boxes size={16} color="white" />
        </div>
        <div>
          <div className="font-bold text-[15.5px] tracking-tight">BoardMind</div>
          <div className="text-[10.5px] text-[var(--text-tertiary)] -mt-0.5">Decision Intelligence</div>
        </div>
      </div>

      {NAV.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2.5 rounded-[11px] text-[13.5px] font-medium border border-transparent transition-all",
              active ? "text-white border-purple-500/30" : "text-[var(--text-secondary)] hover:bg-white/[0.045] hover:text-white"
            )}
            style={active ? { background: "var(--grad-brand-soft)" } : undefined}
          >
            <Icon size={17} className={active ? "drop-shadow-[0_0_6px_rgba(139,92,246,0.6)]" : "opacity-85"} />
            {item.label}
          </Link>
        );
      })}

      <div className="mt-auto pt-3">
        {profile && (
          <div className="flex items-center gap-2.5 px-2.5 py-2.5 rounded-[11px] bg-white/[0.03] border border-white/[0.09]">
            <div className="w-[26px] h-[26px] rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0" style={{ background: "var(--grad-brand)" }}>
              {profile.name.split(" ").map((w) => w[0]).join("").slice(0, 2)}
            </div>
            <div className="min-w-0">
              <div className="text-[12.5px] font-semibold truncate">{profile.name}</div>
              <div className="text-[10.5px] text-[var(--text-tertiary)] truncate">{profile.title}</div>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2.5 px-3 py-2.5 mt-2 rounded-[11px] text-[13.5px] font-medium text-[var(--text-secondary)] hover:bg-white/[0.045] hover:text-white w-full"
        >
          <ArrowLeftRight size={17} className="opacity-85" />
          Switch role
        </button>
      </div>
    </div>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <div className="md:hidden sticky top-0 z-10 flex items-center gap-1 overflow-x-auto px-3 py-2.5 bg-[rgba(9,9,11,0.85)] backdrop-blur-lg border-b border-white/[0.09]">
      {NAV.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-[11px] text-[13px] font-medium shrink-0 whitespace-nowrap",
              active ? "text-white" : "text-[var(--text-secondary)]"
            )}
            style={active ? { background: "var(--grad-brand-soft)" } : undefined}
          >
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

export function PageHeader({ title, sub, right }: { title: string; sub: string; right?: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="flex items-center justify-between gap-4 flex-wrap mb-5.5"
    >
      <div>
        <div className="text-[22px] font-bold tracking-tight">{title}</div>
        <div className="text-[12.5px] text-[var(--text-tertiary)] mt-0.5">{sub}</div>
      </div>
      <div className="flex items-center gap-2.5">{right}</div>
    </motion.div>
  );
}
