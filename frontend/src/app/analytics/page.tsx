"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Upload, Database, Trash2, Loader2, Play, Sparkles, ArrowLeft,
  BarChart3, Activity, AlertTriangle, Users, FileBarChart, RefreshCw, Link2,
} from "lucide-react";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";
import { ResultView } from "@/components/analytics/ResultView";

interface Dataset { dataset_id: string; name: string; rows: number; cols: number; source: string; }
interface Claw { id: string; name: string; desc: string; }

const CLAW_ICONS: Record<string, any> = {
  data_analyst: BarChart3,
  kpi_monitoring: Activity,
  anomaly_detection: AlertTriangle,
  segmentation: Users,
  business_performance: FileBarChart,
};

export default function AnalyticsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [claws, setClaws] = useState<Claw[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedClaw, setSelectedClaw] = useState<string>("data_analyst");
  const [result, setResult] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>("");
  const [dataUrl, setDataUrl] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const api = getApiBaseUrl();

  const fetchDatasets = async () => {
    try {
      const res = await axios.get(`${api}/analytics/datasets`);
      setDatasets(res.data.datasets || []);
      if (!activeId && res.data.datasets?.length) setActiveId(res.data.datasets[0].dataset_id);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    axios.get(`${api}/analytics/claws`).then((r) => setClaws(r.data.claws || [])).catch(() => {});
    fetchDatasets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await axios.post(`${api}/analytics/upload`, form, { headers: { "Content-Type": "multipart/form-data" } });
      await fetchDatasets();
      setActiveId(res.data.dataset.dataset_id);
      setResult(null);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const importDataUrl = async () => {
    if (!dataUrl.trim()) return;
    setUploading(true);
    setError("");
    try {
      const res = await axios.post(`${api}/analytics/import-url`, { url: dataUrl.trim() });
      await fetchDatasets();
      setActiveId(res.data.dataset.dataset_id);
      setDataUrl("");
      setResult(null);
    } catch (e: any) {
      setError(e.response?.data?.detail || "URL import failed.");
    } finally {
      setUploading(false);
    }
  };

  const deleteDataset = async (id: string) => {
    try {
      await axios.delete(`${api}/analytics/dataset/${id}`);
      if (activeId === id) { setActiveId(null); setResult(null); }
      await fetchDatasets();
    } catch { /* ignore */ }
  };

  const runClaw = async () => {
    if (!activeId) { setError("Upload or select a dataset first."); return; }
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await axios.post(`${api}/analytics/run`, { dataset_id: activeId, claw: selectedClaw });
      setResult(res.data.result);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Agent run failed.");
    } finally {
      setRunning(false);
    }
  };

  const activeDataset = datasets.find((d) => d.dataset_id === activeId);

  return (
    <div className="flex h-screen w-full bg-[#030303] text-white overflow-hidden selection:bg-white selection:text-black">
      {/* Background grid */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#8080800A_1px,transparent_1px),linear-gradient(to_bottom,#8080800A_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Sidebar: datasets */}
      <div className="w-[320px] shrink-0 border-r border-white/[0.08] bg-[#050505]/80 backdrop-blur-2xl flex flex-col relative z-10">
        <Link href="/dashboard" className="h-16 flex items-center px-6 border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors group">
          <ArrowLeft className="w-4 h-4 mr-3 text-white/50 group-hover:text-white" />
          <span className="font-semibold tracking-wide text-[0.95rem] text-white/90">Analytics Agents</span>
        </Link>

        <div className="p-5 border-b border-white/[0.06] space-y-3">
          <p className="text-white/40 text-[0.75rem] leading-relaxed">Upload a CSV / Excel file, or paste a direct link to one. No login required.</p>
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.tsv" className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} />
          <button onClick={() => fileRef.current?.click()} disabled={uploading}
            className="w-full py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2 bg-white text-black hover:shadow-[0_0_20px_rgba(255,255,255,0.15)] disabled:opacity-60 transition-all">
            {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
            {uploading ? "Processing..." : "Upload Dataset"}
          </button>
          <div className="flex items-center gap-1.5">
            <input type="text" placeholder="Paste a direct CSV / Excel link…" value={dataUrl}
              onChange={(e) => setDataUrl(e.target.value)} disabled={uploading}
              onKeyDown={(e) => e.key === "Enter" && importDataUrl()}
              className="flex-1 min-w-0 bg-[#0A0A0A]/90 border border-white/10 text-white placeholder-white/30 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-white/20 transition-all text-xs" />
            <button onClick={importDataUrl} disabled={uploading || !dataUrl.trim()}
              className="shrink-0 px-2.5 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white/70 hover:text-white hover:bg-white/10 disabled:opacity-40 transition-all">
              <Link2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-h-0 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[0.7rem] font-semibold text-white/40 uppercase tracking-[0.15em]">Datasets</h3>
            <button onClick={fetchDatasets} className="text-white/30 hover:text-white/70 transition-colors"><RefreshCw className="w-3.5 h-3.5" /></button>
          </div>
          <div className="flex-1 overflow-y-auto space-y-1.5 custom-scrollbar pr-1">
            {datasets.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-white/30 gap-3">
                <Database className="w-6 h-6 opacity-50" /><p className="text-xs">No datasets yet.</p>
              </div>
            ) : datasets.map((d) => (
              <div key={d.dataset_id} onClick={() => { setActiveId(d.dataset_id); setResult(null); }}
                className={`p-3 rounded-lg flex items-center gap-3 cursor-pointer transition-colors group/item ${activeId === d.dataset_id ? "bg-white/[0.08] border border-white/15" : "hover:bg-white/[0.05] border border-transparent"}`}>
                <Database className={`w-4 h-4 shrink-0 ${activeId === d.dataset_id ? "text-white" : "text-white/40"}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate text-white/80">{d.name}</p>
                  <p className="text-[0.7rem] text-white/40">{d.rows} rows · {d.cols} cols · {d.source}</p>
                </div>
                <button onClick={(e) => { e.stopPropagation(); deleteDataset(d.dataset_id); }}
                  className="opacity-0 group-hover/item:opacity-100 text-white/30 hover:text-red-400 transition-all"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 relative z-10 flex flex-col min-w-0 overflow-y-auto custom-scrollbar">
        <div className="max-w-5xl mx-auto w-full p-8 space-y-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Business Analytics Agents</h1>
            <p className="text-white/40 text-sm mt-1">
              {activeDataset ? <>Analyzing <span className="text-white/70">{activeDataset.name}</span> · {activeDataset.rows} rows × {activeDataset.cols} columns</> : "Select or upload a dataset to begin."}
            </p>
          </div>

          {error && <div className="rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm px-4 py-3">{error}</div>}

          {/* Claw selector */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {claws.map((c) => {
              const Icon = CLAW_ICONS[c.id] || Sparkles;
              const active = selectedClaw === c.id;
              return (
                <button key={c.id} onClick={() => setSelectedClaw(c.id)} title={c.desc}
                  className={`text-left p-4 rounded-2xl border transition-all ${active ? "bg-white/[0.07] border-white/25 shadow-[0_0_25px_rgba(255,255,255,0.05)]" : "bg-white/[0.02] border-white/[0.07] hover:border-white/15 hover:bg-white/[0.04]"}`}>
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${active ? "bg-white text-black" : "bg-white/[0.05] text-white/60"}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <p className="text-[0.8rem] font-semibold text-white/85 leading-tight">{c.name.replace(" Claw", "")}</p>
                  <p className="text-[0.68rem] text-white/40 mt-1 leading-snug line-clamp-3">{c.desc}</p>
                </button>
              );
            })}
          </div>

          <button onClick={runClaw} disabled={running || !activeId}
            className="flex items-center justify-center gap-2.5 bg-white text-black px-6 py-3 rounded-full font-medium text-sm hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:hover:scale-100 transition-all shadow-[0_0_30px_rgba(255,255,255,0.12)]">
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? "Agent is analyzing..." : `Run ${claws.find((c) => c.id === selectedClaw)?.name.replace(" Claw", "") || "Agent"}`}
          </button>

          {/* Results */}
          {running && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-3 text-white/50 text-sm py-8">
              <Loader2 className="w-4 h-4 animate-spin" /> Computing statistics and generating insights...
            </motion.div>
          )}
          {!running && result && <ResultView result={result} />}
          {!running && !result && (
            <div className="h-[40vh] flex flex-col items-center justify-center text-white/25 gap-4">
              <Sparkles className="w-10 h-10 opacity-40" />
              <p className="text-sm">Pick an agent and click Run to generate analytics.</p>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
