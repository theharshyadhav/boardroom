"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar, MobileNav } from "@/components/Sidebar";
import { ConfidenceRingDefs } from "@/components/ConfidenceRing";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { roleKey, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !roleKey) router.replace("/login");
  }, [ready, roleKey, router]);

  if (!ready || !roleKey) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[13px] text-[var(--text-tertiary)]">
        Loading BoardMind…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <ConfidenceRingDefs />
      <Sidebar />
      <div className="flex-1 min-w-0">
        <MobileNav />
        <div className="px-7.5 py-5 pb-16 max-md:px-4">{children}</div>
      </div>
    </div>
  );
}
