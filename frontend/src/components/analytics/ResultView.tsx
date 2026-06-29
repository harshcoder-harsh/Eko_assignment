"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, TrendingDown, Minus, AlertTriangle, Users, Activity } from "lucide-react";
import { StatCard, Sparkline, BarList, ChangeBadge } from "./Charts";

function Section({ icon: Icon, title, children }: { icon: any; title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-white/70">
        <Icon className="w-4 h-4 text-white/50" />
        <h3 className="text-sm font-semibold tracking-wide uppercase text-white/50">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function fmt(n: any) {
  if (n === null || n === undefined) return "—";
  if (typeof n !== "number") return String(n);
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
  if (abs >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function dirIcon(d: string) {
  if (d === "increasing") return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
  if (d === "decreasing") return <TrendingDown className="w-3.5 h-3.5 text-red-400" />;
  return <Minus className="w-3.5 h-3.5 text-white/40" />;
}

export function ResultView({ result }: { result: any }) {
  if (!result) return null;
  const { kpis, trends, monitoring, anomalies, segments, cleaning, insight } = result;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {/* Insight narrative */}
      {insight && (
        <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.04] to-transparent p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-white text-black flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.2)]">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="text-sm font-semibold text-white/80">{result.title || "Agent Insight"}</span>
          </div>
          <div className="prose prose-sm prose-invert max-w-none prose-headings:text-white/90 prose-strong:text-white prose-p:text-white/75 prose-li:text-white/75">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{insight}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Cleaning summary */}
      {cleaning && cleaning.actions && (
        <Section icon={Activity} title="Data Cleaning">
          <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4 text-xs text-white/60 space-y-1">
            <p className="text-white/70">
              {cleaning.original_rows} → {cleaning.clean_rows} rows, {cleaning.original_cols} → {cleaning.clean_cols} columns
            </p>
            <ul className="list-disc pl-4 space-y-0.5">
              {cleaning.actions.map((a: string, i: number) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        </Section>
      )}

      {/* KPIs */}
      {kpis && kpis.kpis && kpis.kpis.length > 0 && (
        <Section icon={Activity} title="Key Metrics">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {kpis.kpis.slice(0, 9).map((k: any) => (
              <StatCard
                key={k.name}
                label={k.name}
                value={fmt(k.total)}
                sub={`avg ${fmt(k.average)} · max ${fmt(k.max)}`}
              />
            ))}
          </div>
          {kpis.breakdowns && kpis.breakdowns.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
              {kpis.breakdowns.slice(0, 4).map((b: any) => (
                <div key={b.column} className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4">
                  <p className="text-xs text-white/50 mb-3">{b.column} <span className="text-white/30">· {b.distinct} distinct</span></p>
                  <BarList items={b.top.map((t: any) => ({ label: t.value, value: t.count, sub: `${t.count} (${t.pct}%)` }))} />
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* Trends */}
      {trends && trends.series && trends.series.length > 0 && (
        <Section icon={TrendingUp} title={`Trends (${trends.period || ""})`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {trends.series.map((s: any) => (
              <div key={s.metric} className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white/80 flex items-center gap-2">{dirIcon(s.direction)} {s.metric}</span>
                  <ChangeBadge pct={s.change_pct} />
                </div>
                <Sparkline points={(s.points || []).map((p: any) => p.v)} />
                <div className="flex justify-between text-[0.7rem] text-white/40 mt-1">
                  <span>{fmt(s.first)}</span>
                  <span>peak {fmt(s.peak)}</span>
                  <span>{fmt(s.last)}</span>
                </div>
              </div>
            ))}
          </div>
          {trends.correlations && trends.correlations.length > 0 && (
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4 text-xs text-white/60">
              <p className="text-white/50 mb-2">Strong correlations</p>
              <div className="flex flex-wrap gap-2">
                {trends.correlations.map((c: any, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg bg-white/[0.05] border border-white/[0.06]">
                    {c.a} ↔ {c.b}: <span className={c.r >= 0 ? "text-emerald-400" : "text-red-400"}>r={c.r}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* KPI Monitoring */}
      {monitoring && monitoring.changes && monitoring.changes.length > 0 && (
        <Section icon={Activity} title={`KPI Monitoring (${monitoring.period || ""})`}>
          <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="text-[0.7rem] uppercase text-white/40 border-b border-white/[0.06]">
                <tr>
                  <th className="text-left font-medium px-4 py-2.5">Metric</th>
                  <th className="text-right font-medium px-4 py-2.5">Previous</th>
                  <th className="text-right font-medium px-4 py-2.5">Current</th>
                  <th className="text-right font-medium px-4 py-2.5">Change</th>
                </tr>
              </thead>
              <tbody>
                {monitoring.changes.map((c: any, i: number) => (
                  <tr key={i} className="border-b border-white/[0.04] last:border-0">
                    <td className="px-4 py-2.5 text-white/80">{c.metric}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-white/50">{fmt(c.previous)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-white/80">{fmt(c.current)}</td>
                    <td className="px-4 py-2.5 text-right"><ChangeBadge pct={c.change_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Anomalies */}
      {anomalies && (
        <Section icon={AlertTriangle} title={`Anomalies (${anomalies.total_anomalies ?? 0})`}>
          {anomalies.anomalies && anomalies.anomalies.length > 0 ? (
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] overflow-hidden">
              <table className="w-full text-sm">
                <thead className="text-[0.7rem] uppercase text-white/40 border-b border-white/[0.06]">
                  <tr>
                    <th className="text-left font-medium px-4 py-2.5">Metric</th>
                    <th className="text-right font-medium px-4 py-2.5">Value</th>
                    <th className="text-right font-medium px-4 py-2.5">Z-score</th>
                    <th className="text-left font-medium px-4 py-2.5">When / Row</th>
                    <th className="text-left font-medium px-4 py-2.5">Method</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.anomalies.slice(0, 12).map((a: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.04] last:border-0">
                      <td className="px-4 py-2.5 text-white/80">{a.column}</td>
                      <td className={`px-4 py-2.5 text-right tabular-nums ${a.direction === "high" ? "text-emerald-400" : "text-red-400"}`}>{fmt(a.value)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-white/60">{a.z_score}</td>
                      <td className="px-4 py-2.5 text-white/50 text-xs">{a.when ? String(a.when).slice(0, 10) : `#${a.row_index}`}</td>
                      <td className="px-4 py-2.5 text-white/40 text-xs">{(a.methods || []).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-white/40">No anomalies detected — the data looks healthy.</p>
          )}
        </Section>
      )}

      {/* Segments */}
      {segments && (
        <Section icon={Users} title="Segments">
          {segments.ok ? (
            <>
              <p className="text-xs text-white/40">
                {segments.k} segments · features: {(segments.feature_columns || []).join(", ")} · silhouette {segments.silhouette}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {segments.segments.map((s: any) => (
                  <div key={s.segment} className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white/85">{s.label}</span>
                      <span className="text-xs text-white/40">{s.size} ({s.size_pct}%)</span>
                    </div>
                    <div className="space-y-1">
                      {(s.highlights || []).map((h: any, i: number) => (
                        <div key={i} className="flex items-center justify-between text-xs text-white/55">
                          <span>{h.feature}</span>
                          <span className={h.direction === "above" ? "text-emerald-400" : "text-red-400"}>
                            {h.direction === "above" ? "+" : ""}{h.vs_avg_pct}% vs avg
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-white/40">{segments.reason}</p>
          )}
        </Section>
      )}
    </motion.div>
  );
}
