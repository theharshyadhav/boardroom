import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-[11px] text-[12.5px] font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-[var(--purple)] focus-visible:outline-offset-2",
  {
    variants: {
      variant: {
        default: "bg-white/[0.04] border border-white/[0.09] text-white hover:bg-white/[0.09]",
        primary: "text-white border-none shadow-[0_4px_18px_rgba(139,92,246,0.35)] hover:brightness-110 hover:-translate-y-px [background:var(--grad-brand)]",
        ghost: "bg-transparent border border-transparent text-[var(--text-secondary)] hover:bg-white/[0.05] hover:text-white",
        dangerOutline: "border border-red-400/30 text-red-400 bg-red-400/[0.06] hover:bg-red-400/[0.12]",
      },
      size: {
        default: "px-4 py-2.5",
        sm: "px-2.5 py-1.5 text-[11.5px] rounded-[9px]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
