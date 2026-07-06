"use client";

import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, ArrowLeft, RefreshCw, Clock, Coins, Cpu, AlertTriangle,
  Hash, Zap, X, Search, Layers, FileText, ChevronRight, Loader2,
} from "lucide-react";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";

// ---- types -----------------------------------------------------------------
interface Overview {
  enabled: boolean;
  window_hours?: number;
  total_traces?: number;
  avg_latency_s?: number;
  p95_latency_s?: number;
  total_tokens?: number;
  total_cost?: number;
  error_count?: number;
  error_rate?: number;
  states?: Record<string, number>;
  model_usage?: { model: string; calls: number; tokens: number }[];
  time_series?: { hour: string; count: number }[];
  error?: string;
}
interface TraceRow {
  id: string; name: string; timestamp: string; latency_s: number;
  cost: number; state: string | null; user_id: string | null; tags: string[];
}
interface Span {
  name: string; type: string; start: string; end: string;
  latency_s: number | null; tokens: number; model: string | null;
  level: string; cost: number;
}
interface TraceDetail {
  enabled: boolean; id: string; name: string; timestamp: string;
  latency_s: number; cost: number; total_tokens: number;
  input: unknown; output: unknown; base_time: string | null;
  spans: Span[]; reasoning: unknown; retrieved_docs: { span: string; output: unknown }[];
  error?: string;
}

const WINDOWS = [
  { label: "1h", hours: 1 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
];

const STATE_COLORS: Record<string, string> = {
  RESOLVED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  ESCALATED: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  TICKETED: "text-amber-400 bg-amber-500/10 border-amber-500/20",
};

const TYPE_COLOR: Record<string, string> = {
  AGENT: "bg-violet-500",
  GENERATION: "bg-fuchsia-500",
  RETRIEVER: "bg-sky-500",
  SPAN: "bg-zinc-500",
};

const fmtCost = (c?: number) =>
  c == null ? "$0" : c < 0.01 ? `$${c.toFixed(5)}` : `$${c.toFixed(3)}`;
const fmtTokens = (t?: number) =>
  t == null ? "0" : t >= 1000 ? `${(t / 1000).toFixed(1)}k` : `${t}`;
const fmtLatency = (s?: number | null) =>
  s == null ? "—" : s >= 1 ? `${s.toFixed(2)}s` : `${Math.round(s * 1000)}ms`;

export default function ObservabilityPage() {
  const api = getApiBaseUrl();
  const [hours, setHours] = useState(24);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [traces, setTraces] = useState<TraceRow[]>([]);
  const [selected, setSelected] = useState<TraceDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, tr] = await Promise.all([
        axios.get(`${api}/observability/overview`, { params: { hours } }),
        axios.get(`${api}/observability/traces`, { params: { hours, limit: 100 } }),
      ]);
      setOverview(ov.data);
      setTraces(tr.data.traces || []);
    } catch {
      setOverview({ enabled: false });
    } finally {
      setLoading(false);
    }
}, [api, hours]);


useEffect(() => { load(); }, [load]);

  const openTrace = async (id: string) => {
    setLoadingDetail(true);
    setSelected({ enabled: true, id } as TraceDetail);
    try {
      const r = await axios.get(`${api}/observability/trace/${id}`);
      setSelected(r.data);
    } catch {
      setSelected(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const disabled = overview && overview.enabled === false;
  const filtered = traces.filter(
    (t) => !query || t.name?.toLowerCase().includes(query.toLowerCase()) ||
      t.id?.toLowerCase().includes(query.toLowerCase())
  );
  const maxSeries = Math.max(1, ...(overview?.time_series || []).map((b) => b.count));

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      {/* ambient */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-20 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl animate-blob" />
        <div className="absolute top-40 right-0 w-96 h-96 bg-sky-600/10 rounded-full blur-3xl animate-blob animation-delay-2000" />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 py-8">
        {/* header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-zinc-500 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-violet-400" />
                <h1 className="text-2xl font-bold tracking-tight">AI Observability</h1>
              </div>
              <p className="text-sm text-zinc-500 mt-0.5">
                Every agent run, traced end to end — without leaving FlowClaw.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex glass-light rounded-xl p-1">
              {WINDOWS.map((w) => (
                <button key={w.hours} onClick={() => setHours(w.hours)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    hours === w.hours ? "bg-violet-500/20 text-violet-300" : "text-zinc-500 hover:text-white"
                  }`}>
                  {w.label}
                </button>
              ))}
            </div>
            <button onClick={load} className="p-2.5 glass-light rounded-xl text-zinc-400 hover:text-white transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {disabled ? (
          <EmptyState error={overview?.error} />
        ) : (
          <>
            {/* stat cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
              <Stat icon={Hash} label="Traces" value={overview?.total_traces ?? "—"}
                sub={`last ${WINDOWS.find((w) => w.hours === hours)?.label}`} tint="violet" />
              <Stat icon={Clock} label="Avg latency" value={fmtLatency(overview?.avg_latency_s)}
                sub={`p95 ${fmtLatency(overview?.p95_latency_s)}`} tint="sky" />
              <Stat icon={Zap} label="Tokens" value={fmtTokens(overview?.total_tokens)}
                sub="across generations" tint="fuchsia" />
              <Stat icon={Coins} label="Cost" value={fmtCost(overview?.total_cost)}
                sub="estimated" tint="emerald" />
              <Stat icon={AlertTriangle} label="Errors" value={overview?.error_count ?? 0}
                sub={`${Math.round((overview?.error_rate ?? 0) * 100)}% of runs`} tint="rose" />
            </div>

            {/* charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              {/* traffic */}
              <div className="glass rounded-2xl p-5 lg:col-span-2">
                <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-zinc-300">
                  <Activity className="w-4 h-4 text-violet-400" /> Run volume
                </div>
                {overview?.time_series?.length ? (
                  <div className="flex items-end gap-1 h-32">
                    {overview.time_series.map((b) => (
                      <div key={b.hour} className="flex-1 group relative flex flex-col justify-end">
                        <div className="bg-gradient-to-t from-violet-600 to-violet-400 rounded-t-sm transition-all group-hover:from-violet-500 group-hover:to-violet-300"
                          style={{ height: `${(b.count / maxSeries) * 100}%`, minHeight: "3px" }} />
                        <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] text-zinc-400 opacity-0 group-hover:opacity-100 whitespace-nowrap">
                          {b.count} · {b.hour.slice(11)}h
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <Muted text="No runs in this window." />}
              </div>

              {/* state breakdown */}
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-zinc-300">
                  <Layers className="w-4 h-4 text-sky-400" /> Outcomes
                </div>
                <div className="space-y-3">
                  {Object.entries(overview?.states || {}).length ? (
                    Object.entries(overview!.states!).map(([s, n]) => {
                      const total = Object.values(overview!.states!).reduce((a, b) => a + b, 0);
                      return (
                        <div key={s}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-zinc-300">{s}</span>
                            <span className="text-zinc-500">{n}</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                            <div className={`h-full rounded-full ${
                              s === "ESCALATED" ? "bg-rose-500" : s === "TICKETED" ? "bg-amber-500" : "bg-emerald-500"
                            }`} style={{ width: `${(n / total) * 100}%` }} />
                          </div>
                        </div>
                      );
                    })
                  ) : <Muted text="No outcomes yet." />}
                </div>
              </div>
            </div>

            {/* model usage */}
            {overview?.model_usage && overview.model_usage.length > 0 && (
              <div className="glass rounded-2xl p-5 mb-6">
                <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-zinc-300">
                  <Cpu className="w-4 h-4 text-fuchsia-400" /> Model usage
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {overview.model_usage.map((m) => (
                    <div key={m.model} className="glass-light rounded-xl px-4 py-3">
                      <div className="text-sm font-mono text-zinc-200 truncate">{m.model}</div>
                      <div className="text-xs text-zinc-500 mt-1">
                        {m.calls} calls · {fmtTokens(m.tokens)} tokens
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* recent traces */}
            <div className="glass rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-300">
                  <FileText className="w-4 h-4 text-violet-400" /> Recent traces
                </div>
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-zinc-600 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input value={query} onChange={(e) => setQuery(e.target.value)}
                    placeholder="Filter by name or id"
                    className="bg-white/5 rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-violet-500/40 w-52" />
                </div>
              </div>
              <div className="divide-y divide-white/5 max-h-[520px] overflow-y-auto">
                {loading ? (
                  <div className="p-10 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-zinc-600" /></div>
                ) : filtered.length ? filtered.map((t) => (
                  <button key={t.id} onClick={() => openTrace(t.id)}
                    className="w-full flex items-center gap-4 px-5 py-3 hover:bg-white/[0.03] transition-colors text-left group">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-zinc-200 truncate">{t.name || "trace"}</span>
                        {t.state && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-md border ${STATE_COLORS[t.state] || "text-zinc-400 bg-white/5 border-white/10"}`}>
                            {t.state}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-zinc-600 font-mono truncate mt-0.5">{t.id}</div>
                    </div>
                    <div className="hidden sm:flex items-center gap-5 text-xs text-zinc-500 shrink-0">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{fmtLatency(t.latency_s)}</span>
                      <span className="flex items-center gap-1"><Coins className="w-3 h-3" />{fmtCost(t.cost)}</span>
                      <span className="w-28 text-right text-zinc-600">{t.timestamp?.slice(0, 19).replace("T", " ")}</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-zinc-700 group-hover:text-zinc-400 shrink-0" />
                  </button>
                )) : <div className="p-10 text-center text-sm text-zinc-600">No traces match.</div>}
              </div>
            </div>
          </>
        )}
      </div>

      {/* detail slide-over */}
      <AnimatePresence>
        {selected && (
          <TraceDrawer detail={selected} loading={loadingDetail} onClose={() => setSelected(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}

// ---- sub-components ---------------------------------------------------------
function Stat({ icon: Icon, label, value, sub, tint }: {
    icon: React.ComponentType<{ className?: string }>;
    label: string; value: React.ReactNode; sub: string; tint: string;
  }) {
  const tints: Record<string, string> = {
    violet: "text-violet-400", sky: "text-sky-400", fuchsia: "text-fuchsia-400",
    emerald: "text-emerald-400", rose: "text-rose-400",
  };
  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium mb-2">
        <Icon className={`w-3.5 h-3.5 ${tints[tint]}`} /> {label}
      </div>
      <div className="text-2xl font-bold tracking-tight">{value}</div>
      <div className="text-[11px] text-zinc-600 mt-1">{sub}</div>
    </div>
  );
}

function Muted({ text }: { text: string }) {
  return <div className="text-xs text-zinc-600 py-8 text-center">{text}</div>;
}

function EmptyState({ error }: { error?: string }) {
  return (
    <div className="glass rounded-2xl p-12 text-center">
      <Activity className="w-10 h-10 text-zinc-700 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-zinc-200 mb-1">Tracing isn&apos;t connected</h3>
      <p className="text-sm text-zinc-500 max-w-md mx-auto">
        Set <code className="text-violet-400">LANGFUSE_PUBLIC_KEY</code> and{" "}
        <code className="text-violet-400">LANGFUSE_SECRET_KEY</code> in the backend
        environment, then run a support query to populate this dashboard.
      </p>
      {error && <p className="text-xs text-rose-400/70 mt-4 font-mono">{error}</p>}
    </div>
  );
}

function TraceDrawer({ detail, loading, onClose }: { detail: TraceDetail; loading: boolean; onClose: () => void }) {
  // build timeline offsets
  const base = detail.base_time ? Date.parse(detail.base_time) : null;
  const spanEnds = (detail.spans || []).map((s) => (s.end ? Date.parse(s.end) : 0));
  const totalMs = base && spanEnds.length ? Math.max(...spanEnds) - base : 0;

  return (
    <>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose} className="fixed inset-0 bg-black/60 z-30" />
      <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
        className="fixed right-0 top-0 h-full w-full max-w-2xl glass border-l border-white/10 z-40 overflow-y-auto">
        <div className="sticky top-0 glass px-6 py-4 border-b border-white/10 flex items-center justify-between z-10">
          <div className="min-w-0">
            <div className="font-semibold text-zinc-100 truncate">{detail.name || "Trace"}</div>
            <div className="text-[11px] text-zinc-600 font-mono truncate">{detail.id}</div>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {loading ? (
          <div className="p-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-600" /></div>
        ) : detail.error ? (
          <div className="p-6 text-sm text-rose-400/80 font-mono">{detail.error}</div>
        ) : (
          <div className="p-6 space-y-6">
            {/* metrics */}
            <div className="grid grid-cols-3 gap-3">
              <MiniStat label="Latency" value={fmtLatency(detail.latency_s)} />
              <MiniStat label="Tokens" value={fmtTokens(detail.total_tokens)} />
              <MiniStat label="Cost" value={fmtCost(detail.cost)} />
            </div>

            {/* timeline */}
            <section>
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-3">Workflow timeline</h4>
              <div className="space-y-1.5">
                {(detail.spans || []).map((s, i) => {
                  const start = s.start ? Date.parse(s.start) : base || 0;
                  const end = s.end ? Date.parse(s.end) : start;
                  const left = base && totalMs ? ((start - base) / totalMs) * 100 : 0;
                  const width = totalMs ? Math.max(1.5, ((end - start) / totalMs) * 100) : 100;
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-36 shrink-0 text-right">
                        <span className="text-xs text-zinc-300 truncate">{s.name}</span>
                      </div>
                      <div className="flex-1 relative h-5 rounded bg-white/[0.03]">
                        <div className={`absolute h-full rounded ${TYPE_COLOR[s.type] || "bg-zinc-500"} ${s.level === "WARNING" || s.level === "ERROR" ? "ring-1 ring-rose-400" : ""}`}
                          style={{ left: `${left}%`, width: `${width}%` }} title={`${s.type} · ${fmtLatency(s.latency_s)}`} />
                      </div>
                      <div className="w-14 shrink-0 text-[11px] text-zinc-500 text-right">{fmtLatency(s.latency_s)}</div>
                    </div>
                  );
                })}
              </div>
              {/* legend */}
              <div className="flex flex-wrap gap-3 mt-3">
                {Object.entries(TYPE_COLOR).map(([t, c]) => (
                  <span key={t} className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                    <span className={`w-2.5 h-2.5 rounded-sm ${c}`} /> {t}
                  </span>
                ))}
              </div>
            </section>

            {/* reasoning */}
            {detail.reasoning != null && (
              <section>
                <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Reasoning (draft)</h4>
                <div className="glass-light rounded-xl p-4 text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                  {typeof detail.reasoning === "string" ? detail.reasoning : JSON.stringify(detail.reasoning, null, 2)}
                </div>
              </section>
            )}

            {/* retrieved docs */}
            {detail.retrieved_docs && detail.retrieved_docs.length > 0 && (
              <section>
                <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Retrieved context</h4>
                <div className="space-y-2">
                  {detail.retrieved_docs.map((d, i) => (
                    <div key={i} className="glass-light rounded-xl p-4">
                      <div className="text-[11px] text-sky-400 font-mono mb-2">{d.span}</div>
                      <pre className="text-xs text-zinc-400 whitespace-pre-wrap break-words overflow-x-auto">
                        {typeof d.output === "string" ? d.output : JSON.stringify(d.output, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* raw io */}
            <section>
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">Trace output</h4>
              <pre className="glass-light rounded-xl p-4 text-xs text-zinc-400 whitespace-pre-wrap break-words overflow-x-auto">
                {typeof detail.output === "string" ? detail.output : JSON.stringify(detail.output, null, 2)}
              </pre>
            </section>
          </div>
        )}
      </motion.div>
    </>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-light rounded-xl p-3 text-center">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-bold text-zinc-100 mt-1">{value}</div>
    </div>
  );
}