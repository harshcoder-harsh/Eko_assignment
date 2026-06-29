"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Loader2, CheckCircle2, AlertCircle, Upload, Link2, FileText } from "lucide-react";
import axios from "axios";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";

export function SyncPanel({ onSyncSuccess }: { onSyncSuccess: (docs: { id: string, name: string, status: string }[]) => void }) {
  const [status, setStatus] = useState<"idle" | "success" | "error" | "processing">("idle");
  const [message, setMessage] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [docUploading, setDocUploading] = useState(false);
  const [docUrl, setDocUrl] = useState("");
  const docFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    const checkStatus = async () => {
      try {
        const res = await axios.get(`${getApiBaseUrl()}/storage/stats`);
        setStats(res.data);
      } catch {
        // ignore polling errors
      }
    };
    checkStatus();
    interval = setInterval(checkStatus, 5000);
    return () => { if (interval) clearInterval(interval); };
  }, []);

  const handleDocUpload = async (file: File) => {
    setDocUploading(true);
    setStatus("idle");
    setMessage(`Uploading ${file.name}...`);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await axios.post(`${getApiBaseUrl()}/documents/upload`, form, { headers: { "Content-Type": "multipart/form-data" } });
      setStatus("success");
      setMessage(`Indexed "${res.data.document.name}" (${res.data.document.chunks} chunks). Ask away!`);
      onSyncSuccess([{ id: res.data.document.id, name: res.data.document.name, status: "Indexed" }]);
    } catch (err: any) {
      setStatus("error");
      setMessage(err.response?.data?.detail || "Upload failed.");
    } finally {
      setDocUploading(false);
      if (docFileRef.current) docFileRef.current.value = "";
    }
  };

  const handleDocUrl = async () => {
    if (!docUrl.trim()) return;
    setDocUploading(true);
    setStatus("idle");
    setMessage("Fetching document from URL...");
    try {
      const res = await axios.post(`${getApiBaseUrl()}/documents/import-url`, { url: docUrl.trim() });
      setStatus("success");
      setMessage(`Indexed "${res.data.document.name}" (${res.data.document.chunks} chunks). Ask away!`);
      onSyncSuccess([{ id: res.data.document.id, name: res.data.document.name, status: "Indexed" }]);
      setDocUrl("");
    } catch (err: any) {
      setStatus("error");
      setMessage(err.response?.data?.detail || "Import failed.");
    } finally {
      setDocUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 relative">
      <p className="text-white/40 text-[0.75rem] leading-relaxed font-normal px-1 mb-1">
        Upload a PDF, DOCX or TXT to chat with it, or paste a direct file link. No login required.
      </p>

      <div className="rounded-xl bg-white/[0.03] border border-white/[0.07] p-3 flex flex-col gap-2.5">
        <p className="text-white/50 text-[0.7rem] font-semibold uppercase tracking-wider flex items-center gap-1.5">
          <Upload className="w-3 h-3" /> Add a Document
        </p>
        <input ref={docFileRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
          onChange={(e) => e.target.files?.[0] && handleDocUpload(e.target.files[0])} />
        <button onClick={() => docFileRef.current?.click()} disabled={docUploading}
          className="w-full py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2 bg-white text-black hover:shadow-[0_0_15px_rgba(255,255,255,0.15)] disabled:opacity-60 transition-all">
          {docUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
          {docUploading ? "Working..." : "Upload PDF / DOCX / TXT"}
        </button>
        <div className="flex items-center gap-1.5">
          <input type="text" placeholder="Paste a direct file link…" value={docUrl}
            onChange={(e) => setDocUrl(e.target.value)} disabled={docUploading}
            onKeyDown={(e) => e.key === "Enter" && handleDocUrl()}
            className="flex-1 min-w-0 bg-[#0A0A0A]/90 border border-white/10 text-white placeholder-white/30 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-white/20 transition-all text-xs" />
          <button onClick={handleDocUrl} disabled={docUploading || !docUrl.trim()}
            className="shrink-0 px-2.5 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white/70 hover:text-white hover:bg-white/10 disabled:opacity-40 transition-all" title="Import from URL">
            <Link2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {status !== "idle" && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-1 p-3 rounded-xl flex items-start gap-2.5 text-xs ${
            status === "success" ? "bg-white/[0.05] border border-white/10 text-white/80" :
            status === "processing" ? "bg-blue-500/10 border border-blue-500/20 text-blue-300" :
            "bg-red-500/10 border border-red-500/20 text-red-400"
          }`}
        >
          {status === "success" ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-white/50" /> :
           status === "processing" ? <Loader2 className="w-3.5 h-3.5 shrink-0 mt-0.5 animate-spin text-blue-400" /> :
           <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
          <span className="leading-relaxed">{message}</span>
        </motion.div>
      )}

      {stats && (
        <div className="mt-1 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] text-white/60 text-[11px] space-y-1">
          <div className="flex justify-between"><span>Status</span><span className="text-white/80">{stats.status || "—"}</span></div>
          <div className="flex justify-between"><span>Docs Indexed</span><span className="text-white/80">{typeof stats.docs_indexed === "number" ? stats.docs_indexed : "—"}</span></div>
          <div className="flex justify-between"><span>Total Chunks</span><span className="text-white/80">{typeof stats.total_chunks === "number" ? stats.total_chunks : "—"}</span></div>
          <div className="flex justify-between"><span>Vectors</span><span className="text-white/80">{typeof stats.vectors === "number" ? stats.vectors : "—"}</span></div>
        </div>
      )}
    </div>
  );
}
