import type { ConfidenceBand } from "@/lib/types";

const GRADIENTS: Record<ConfidenceBand, string> = {
  high: "url(#gradHigh)",
  medium: "url(#gradMedium)",
  low: "url(#gradLow)",
};

export function ConfidenceRing({ score, band, size = 38 }: { score: number; band: ConfidenceBand; size?: number }) {
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - score / 100);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 38 38" width={size} height={size} className="-rotate-90">
        <circle cx="19" cy="19" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={3.5} />
        <circle
          cx="19" cy="19" r={r} fill="none" strokeWidth={3.5} strokeLinecap="round"
          stroke={GRADIENTS[band]}
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[9.5px] font-bold font-mono-tab">{score}</div>
    </div>
  );
}

/** Renders the gradient <defs> once at the app root; ConfidenceRing instances reference them by id. */
export function ConfidenceRingDefs() {
  return (
    <svg width="0" height="0" className="absolute">
      <defs>
        <linearGradient id="gradHigh" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#34D399" /><stop offset="100%" stopColor="#22D3EE" />
        </linearGradient>
        <linearGradient id="gradMedium" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FBBF24" /><stop offset="100%" stopColor="#F59E0B" />
        </linearGradient>
        <linearGradient id="gradLow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#F87171" /><stop offset="100%" stopColor="#FB7185" />
        </linearGradient>
      </defs>
    </svg>
  );
}
