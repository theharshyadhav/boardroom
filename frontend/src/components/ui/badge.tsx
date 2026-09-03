import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 text-[10.5px] font-bold px-2.5 py-1 rounded-md uppercase tracking-wide", {
  variants: {
    tone: {
      critical: "bg-red-400/[0.14] text-red-400",
      high: "bg-amber-400/[0.14] text-amber-400",
      medium: "bg-purple-400/[0.14] text-purple-300",
      low: "bg-slate-400/[0.14] text-slate-400",
      neutral: "bg-white/[0.05] border border-white/[0.09] text-[var(--text-secondary)] normal-case font-medium",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
