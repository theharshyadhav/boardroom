"use client";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

export function Slider({ className, ...props }: React.ComponentProps<typeof SliderPrimitive.Root>) {
  return (
    <SliderPrimitive.Root className={cn("relative flex items-center select-none touch-none w-full h-5", className)} {...props}>
      <SliderPrimitive.Track className="bg-white/[0.09] relative grow rounded-full h-[5px]">
        <SliderPrimitive.Range className="absolute h-full rounded-full" style={{ background: "var(--grad-brand)" }} />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        className="block w-[17px] h-[17px] rounded-full border-2 border-white/70 cursor-pointer shadow-[0_2px_8px_rgba(139,92,246,0.6)] focus-visible:outline-2 focus-visible:outline-[var(--purple)]"
        style={{ background: "var(--grad-brand)" }}
      />
    </SliderPrimitive.Root>
  );
}
