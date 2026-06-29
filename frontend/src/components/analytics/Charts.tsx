"use client";

// Lightweight, dependency-free chart primitives for the Analytics dashboard.
// All rendered with inline SVG / CSS so they work under the strict bundle.

export function StatCard({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: "up" | "down" | "neutral" }) {
  const accentColor =
    accent === "up" ? "text-emerald-400" : accent === "down" ? "text-red-400" : "text-white/90";
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4 flex flex-col gap-1 min-w-0">
      <span className="text-[0.65rem] uppercase tracking-wider text-white/40 truncate">{label}</span>
      <span className={`text-xl font-semibold tabular-nums ${accentColor}`}>{value}</span>
      {sub && <span className="text-[0.7rem] text-white/40 truncate">{sub}</span>}
    </div>
  );
}

export function Sparkline({ points, height = 44 }: { points: number[]; height?: number }) {
  if (!points || points.length < 2) return null;
  const w = 220;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = w / (points.length - 1);
  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${(height - ((p - min) / range) * (height - 6) - 3).toFixed(1)}`)
    .join(" ");
  const last = points[points.length - 1];
  const first = points[0];
  const rising = last >= first;
  const stroke = rising ? "#34d399" : "#f87171";
  // Unique, selector-safe gradient id (hex colors can't go in DOM ids).
  const gid = `spark-${rising ? "up" : "down"}-${points.length}-${Math.round(min)}-${Math.round(max)}`;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} preserveAspectRatio="none" className="overflow-visible">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L ${w} ${height} L 0 ${height} Z`} fill={`url(#${gid})`} stroke="none" />
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function BarList({ items }: { items: { label: string; value: number; sub?: string }[] }) {
  if (!items || items.length === 0) return null;
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 1);
  return (
    <div className="space-y-2">
      {items.map((it, idx) => {
        const pct = (Math.abs(it.value) / max) * 100;
        const neg = it.value < 0;
        return (
          <div key={idx} className="flex items-center gap-3 text-xs">
            <span className="w-28 shrink-0 truncate text-white/60" title={it.label}>{it.label}</span>
            <div className="flex-1 h-5 rounded-md bg-white/[0.04] overflow-hidden relative">
              <div
                className={`h-full rounded-md ${neg ? "bg-red-400/50" : "bg-gradient-to-r from-white/40 to-white/70"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-20 shrink-0 text-right tabular-nums text-white/80">{it.sub ?? it.value}</span>
          </div>
        );
      })}
    </div>
  );
}

export function ChangeBadge({ pct }: { pct: number | null }) {
  if (pct === null || pct === undefined) return <span className="text-white/40">—</span>;
  const up = pct >= 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${up ? "text-emerald-400" : "text-red-400"}`}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}%
    </span>
  );
}
