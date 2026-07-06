"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, LifeBuoy, Send, ShieldAlert, CheckCircle, Ticket, 
  HelpCircle, RefreshCw, Loader2, Play, Eye, BookOpen, Clock, Activity
} from "lucide-react";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";

interface TicketItem {
  ticket_id: string;
  user_email: string;
  query: string;
  issue_type: string;
  severity: string;
  draft_response: string;
  status: string;
  escalation_reason?: string;
  created_at: string;
}

interface AuditEvent {
  step: string;
  detail: any;
  timestamp: string;
}

interface AuditRun {
  run_id: string;
  user_email: string;
  query: string;
  events: AuditEvent[];
  state: string;
  started_at: string;
}

export default function SupportClawPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeRun, setActiveRun] = useState<any>(null);
  const [auditDetail, setAuditDetail] = useState<AuditRun | null>(null);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [activeTab, setActiveTab] = useState<"reasoning" | "audit" | "tickets">("reasoning");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const api = getApiBaseUrl();

  const fetchTickets = async () => {
    try {
      const res = await axios.get(`${api}/support/tickets?mine_only=false`);
      setTickets(res.data.tickets || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setErrorMessage("");
    setSuccessMessage("");
    try {
      const res = await handleApiPost(`${api}/support/resolve`, { query: query.trim() });
      setActiveRun(res.data);
      if (res.data.run_id) {
        // Instantly load the audit trail for this run
        const auditRes = await handleApiGet(`${api}/support/audit/${res.data.run_id}`);
        setAuditDetail(auditRes.data);
        setActiveTab("reasoning");
      }
      setQuery("");
      fetchTickets();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "An error occurred during workflow execution.");
    } finally {
      setLoading(false);
    }
  };

  const loadAuditTrail = async (runId: string) => {
    try {
      const res = await handleApiGet(`${api}/support/audit/${runId}`);
      setAuditDetail(res.data);
      setActiveTab("audit");
    } catch {
      setErrorMessage("Could not load audit log for the selected run.");
    }
  };

  const resolveTicket = async (ticketId: string) => {
    try {
      await handleApiPost(`${api}/support/ticket/${ticketId}/resolve`, {});
      setSuccessMessage("Ticket resolved successfully!");
      fetchTickets();
      if (activeRun?.ticket?.ticket_id === ticketId) {
        setActiveRun((prev: any) => prev ? { ...prev, ticket: { ...prev.ticket, status: "resolved" } } : null);
      }
    } catch {
      setErrorMessage("Failed to resolve ticket.");
    }
  };

  // Safe API helper methods to catch & return mock answers if backend drops offline
  const handleApiGet = async (url: string) => {
    try {
      return await axios.get(url);
    } catch (e) {
      // Fallback mocks for offline testing
      if (url.includes("/support/audit")) {
        const runId = url.split("/").pop();
        return {
          data: {
            run_id: runId || "mock-id",
            user_email: "default_user",
            query: activeRun?.query || "Test Support Inquiry",
            state: activeRun?.state || "ESCALATED",
            started_at: new Date().toISOString(),
            events: [
              { step: "RECEIVED", timestamp: new Date().toISOString(), detail: { query: activeRun?.query } },
              { step: "CLASSIFIED", timestamp: new Date().toISOString(), detail: activeRun?.classification || { issue_type: "billing", severity: "medium", reasoning: "Mock reasoning path" } },
              { step: "SOP_RETRIEVED", timestamp: new Date().toISOString(), detail: { scoped_to_sop: true, num_sources: 1, source_names: ["Refund_SOP.txt"] } },
              { step: "DRAFTED", timestamp: new Date().toISOString(), detail: { draft_response: activeRun?.draft_response } },
              ...(activeRun?.state === "ESCALATED" ? [{ step: "ESCALATED", timestamp: new Date().toISOString(), detail: { reason: "Mandatory Escalation Rules applied." } }] : [])
            ]
          }
        };
      }
      throw e;
    }
  };

  const handleApiPost = async (url: string, payload: any) => {
    try {
      return await axios.post(url, payload);
    } catch (e) {
      // Return simulated Hermes Agent run if API endpoint fails locally (offline fallback)
      if (url.includes("/support/resolve")) {
        const isCritical = payload.query.toLowerCase().includes("down") || payload.query.toLowerCase().includes("critical");
        const mockRun = {
          run_id: Math.random().toString(36).substring(7),
          state: isCritical ? "ESCALATED" : "RESOLVED",
          classification: {
            issue_type: payload.query.toLowerCase().includes("refund") ? "billing" : "technical",
            severity: isCritical ? "critical" : "low",
            reasoning: "Reasoning generated under local sandbox execution (offline fallback mode)."
          },
          draft_response: isCritical 
            ? "I don't have enough information in our SOPs to resolve critical production server downtime issues. I've raised an escalation ticket for immediate engineering assistance." 
            : "To request a refund, navigate to Settings > Billing > Request Refund. Your pro-rated refund will be processed within 5-10 business days.",
          sources: [{ doc_id: "refund_sop_chunk_0", name: "Refund_SOP.txt", chunk_text: "Mock text chunk" }],
          scoped_to_sop: true,
          ticket: isCritical ? {
            ticket_id: Math.random().toString(36).substring(7),
            user_email: "default_user",
            query: payload.query,
            issue_type: "technical",
            severity: "critical",
            draft_response: "Downtime alert received.",
            status: "escalated"
          } : null
        };
        return { data: mockRun };
      }
      throw e;
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#030303] text-white overflow-hidden selection:bg-white selection:text-black">
      
      {/* Background grid */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#8080800A_1px,transparent_1px),linear-gradient(to_bottom,#8080800A_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Main Container */}
      <div className="flex flex-col flex-1 relative z-10 min-w-0">
        
        {/* Header */}
        <header className="h-16 shrink-0 border-b border-white/[0.08] bg-[#050505]/60 backdrop-blur-md flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="p-2 -ml-2 rounded-lg hover:bg-white/[0.04] transition-colors group">
              <ArrowLeft className="w-4 h-4 text-white/50 group-hover:text-white transition-colors" />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center">
                <LifeBuoy className="w-3.5 h-3.5 text-black" />
              </div>
              <h1 className="font-semibold tracking-wide text-sm text-white/90">Support Escalation Claw</h1>
            </div>
            <span className="text-[0.65rem] bg-white/10 px-2 py-0.5 rounded-full text-white/60 font-mono tracking-wider font-semibold">HERMES-AGENT ACTIVE</span>
          </div>

          <button onClick={fetchTickets} className="p-2 rounded-lg hover:bg-white/[0.04] text-white/40 hover:text-white/80 transition-all flex items-center gap-1.5 text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            Sync Tickets
          </button>
        </header>

        {/* Content Body Layout */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          
          {/* Left panel: Chat Interface */}
          <div className="flex-1 flex flex-col min-w-0 border-r border-white/[0.08]">
            
            {/* Run details overview */}
            {activeRun && (
              <div className="p-4 border-b border-white/[0.08] bg-white/[0.02] flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-white/40">Run ID:</span>
                  <span className="font-mono text-white/70 bg-white/[0.06] px-2 py-0.5 rounded">{activeRun.run_id}</span>
                  <span className="text-white/40">State:</span>
                  <span className={`px-2 py-0.5 rounded font-medium flex items-center gap-1 ${
                    activeRun.state === "RESOLVED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                    activeRun.state === "ESCALATED" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                    "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {activeRun.state === "RESOLVED" ? <CheckCircle className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                    {activeRun.state}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button onClick={() => loadAuditTrail(activeRun.run_id)} className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 hover:bg-white/10 hover:text-white text-white/80 flex items-center gap-1 transition-all">
                    <Eye className="w-3 h-3" />
                    Inspect Log
                  </button>
                </div>
              </div>
            )}

            {/* Error notifications */}
            {errorMessage && (
              <div className="m-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                {errorMessage}
              </div>
            )}

            {/* Success notifications */}
            {successMessage && (
              <div className="m-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 shrink-0" />
                {successMessage}
              </div>
            )}

            {/* Response Display Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {!activeRun ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto">
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.02] border border-white/[0.08] flex items-center justify-center mb-4 text-white/50">
                    <LifeBuoy className="w-6 h-6 animate-pulse" />
                  </div>
                  <h3 className="font-semibold text-sm mb-1.5">Launch Resolution Flow</h3>
                  <p className="text-xs text-white/40 leading-relaxed">
                    Submit customer support cases below. The autonomous Hermes agent will retrieve SOP documents, run classification models, and decide whether to resolve or safely escalate the query.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Customer query message bubble */}
                  <div className="flex justify-end">
                    <div className="max-w-[70%] bg-white/[0.06] border border-white/[0.08] rounded-2xl px-4 py-3 text-sm text-white/90">
                      <p className="text-[0.65rem] text-white/40 mb-1 uppercase tracking-wider font-semibold">User Case</p>
                      <p className="leading-relaxed whitespace-pre-wrap">{activeRun.query || activeRun.ticket?.query}</p>
                    </div>
                  </div>

                  {/* Hermes agent reply bubble */}
                  <div className="flex justify-start">
                    <div className="max-w-[85%] bg-[#0A0A0A] border border-white/[0.08] rounded-2xl px-5 py-4 text-sm relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-24 h-24 bg-white/[0.01] rounded-full blur-2xl" />
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[0.65rem] text-white/50 uppercase tracking-wider font-semibold bg-white/10 px-1.5 py-0.5 rounded">HERMES DRAFT</span>
                        {activeRun.scoped_to_sop ? (
                          <span className="text-[0.65rem] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded flex items-center gap-1">
                            <BookOpen className="w-2.5 h-2.5" /> SOP Grounded
                          </span>
                        ) : (
                          <span className="text-[0.65rem] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded">
                            Unscoped Search
                          </span>
                        )}
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap text-white/90">{activeRun.draft_response}</p>

                      {/* Source Citations */}
                      {activeRun.sources && activeRun.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-white/[0.06] space-y-1">
                          <p className="text-[0.65rem] font-semibold text-white/40 uppercase tracking-wider">Citations ({activeRun.sources.length})</p>
                          <div className="flex flex-wrap gap-1.5">
                            {activeRun.sources.map((src: any, idx: number) => (
                              <span key={idx} className="text-[0.65rem] px-2 py-0.5 rounded bg-white/[0.05] border border-white/[0.05] text-white/60 flex items-center gap-1 font-mono">
                                <BookOpen className="w-2.5 h-2.5 text-white/30" />
                                {src.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Active Escalated Ticket Notification */}
                  {activeRun.ticket && (
                    <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/[0.03] space-y-3">
                      <div className="flex items-center gap-2">
                        <Ticket className="w-4 h-4 text-red-400" />
                        <span className="font-semibold text-xs text-red-400 uppercase tracking-wider">Escalated Ticket Issued</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-xs bg-white/[0.02] p-3 rounded-lg border border-white/[0.04]">
                        <div>
                          <span className="text-white/40 block">Ticket ID:</span>
                          <span className="font-mono text-white/70">{activeRun.ticket.ticket_id}</span>
                        </div>
                        <div>
                          <span className="text-white/40 block">Status:</span>
                          <span className={`capitalize font-semibold ${
                            activeRun.ticket.status === "resolved" ? "text-emerald-400" : "text-red-400"
                          }`}>{activeRun.ticket.status}</span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-white/40 block">Escalation Reason:</span>
                          <span className="text-white/70 italic">"{activeRun.ticket.escalation_reason || 'Requires manual staff assistance.'}"</span>
                        </div>
                      </div>

                      {activeRun.ticket.status !== "resolved" && (
                        <button onClick={() => resolveTicket(activeRun.ticket.ticket_id)}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500 text-black hover:bg-emerald-400 transition-all flex items-center gap-1 shadow-lg shadow-emerald-500/10">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Mark Ticket Resolved
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom input section */}
            <form onSubmit={handleResolve} className="p-4 pb-6 border-t border-white/[0.08] bg-[#050505]/40 flex items-center gap-3 relative">
              <input type="text" placeholder="Submit customer case query (e.g. production server is down)..."
                value={query} onChange={(e) => setQuery(e.target.value)} disabled={loading}
                className="flex-1 bg-[#0A0A0A] border border-white/10 text-white placeholder-white/30 rounded-xl pl-6 pr-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-white/20 transition-all" />
              <button type="submit" disabled={loading || !query.trim()}
                className="w-10 h-10 rounded-xl bg-white text-black hover:shadow-[0_0_15px_rgba(255,255,255,0.2)] disabled:opacity-40 hover:scale-[1.02] flex items-center justify-center shrink-0 transition-all">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>
          </div>

          {/* Right panel: Telemetry Tabbed View */}
          <div className="w-[380px] shrink-0 flex flex-col min-h-0 bg-[#050505]/40">
            
            {/* Tabs */}
            <div className="grid grid-cols-3 border-b border-white/[0.08] h-12 shrink-0">
              <button onClick={() => setActiveTab("reasoning")}
                className={`text-xs font-medium border-b-2 flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === "reasoning" ? "border-white text-white bg-white/[0.02]" : "border-transparent text-white/40 hover:text-white/70"
                }`}>
                <Activity className="w-3.5 h-3.5" />
                Reasoning
              </button>
              <button onClick={() => setActiveTab("audit")}
                className={`text-xs font-medium border-b-2 flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === "audit" ? "border-white text-white bg-white/[0.02]" : "border-transparent text-white/40 hover:text-white/70"
                }`}>
                <Clock className="w-3.5 h-3.5" />
                Audit
              </button>
              <button onClick={() => setActiveTab("tickets")}
                className={`text-xs font-medium border-b-2 flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === "tickets" ? "border-white text-white bg-white/[0.02]" : "border-transparent text-white/40 hover:text-white/70"
                }`}>
                <Ticket className="w-3.5 h-3.5" />
                Tickets ({tickets.length})
              </button>
            </div>

            {/* Tab Panels */}
            <div className="flex-1 overflow-y-auto p-4">
              <AnimatePresence mode="wait">
                
                {/* Reasoning Tab */}
                {activeTab === "reasoning" && (
                  <motion.div key="reasoning" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} className="space-y-4">
                    {activeRun?.classification ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] space-y-3">
                          <h4 className="text-xs font-bold text-white/50 uppercase tracking-wider">Hermes Classifier Telemetry</h4>
                          <div className="space-y-2.5">
                            <div className="flex items-center justify-between text-xs border-b border-white/[0.04] pb-2">
                              <span className="text-white/40">Issue Type:</span>
                              <span className="font-semibold capitalize text-white/80 bg-white/10 px-2 py-0.5 rounded font-mono">{activeRun.classification.issue_type}</span>
                            </div>
                            <div className="flex items-center justify-between text-xs border-b border-white/[0.04] pb-2">
                              <span className="text-white/40">Severity:</span>
                              <span className={`font-semibold capitalize px-2 py-0.5 rounded font-mono ${
                                activeRun.classification.severity === "critical" || activeRun.classification.severity === "high" 
                                  ? "bg-red-500/10 text-red-400" 
                                  : "bg-white/10 text-white/80"
                              }`}>{activeRun.classification.severity}</span>
                            </div>
                          </div>
                          <div className="text-xs pt-1">
                            <span className="text-white/40 block mb-1">Reasoning Analysis:</span>
                            <p className="text-white/80 italic leading-relaxed bg-[#0A0A0A] p-2.5 rounded-lg border border-white/5">
                              "{activeRun.classification.reasoning}"
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="h-48 flex items-center justify-center text-center p-8 text-white/30 text-xs">
                        No active reasoning logs. Submit a customer case query to trace real-time execution.
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Audit Trail Tab */}
                {activeTab === "audit" && (
                  <motion.div key="audit" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} className="space-y-4">
                    {auditDetail ? (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[0.68rem] text-white/40 uppercase tracking-wider font-semibold">Workflow Steps Replay</span>
                          <span className="text-[0.65rem] font-mono bg-white/10 px-2 py-0.5 rounded text-white/60">{auditDetail.state}</span>
                        </div>
                        
                        <div className="relative border-l border-white/10 ml-2.5 pl-5 space-y-5">
                          {auditDetail.events.map((evt, idx) => (
                            <div key={idx} className="relative">
                              {/* Step circle marker */}
                              <div className="absolute -left-[26px] top-0.5 w-3 h-3 rounded-full bg-white border-2 border-black ring-2 ring-white/10" />
                              <div className="space-y-1">
                                <p className="text-xs font-semibold tracking-wide text-white/90">{evt.step}</p>
                                <p className="text-[0.68rem] text-white/40">{new Date(evt.timestamp).toLocaleTimeString()}</p>
                                
                                {/* Step details preview */}
                                {evt.detail && Object.keys(evt.detail).length > 0 && (
                                  <pre className="text-[0.68rem] bg-black/60 border border-white/[0.04] p-2 rounded-lg font-mono text-white/50 max-h-24 overflow-y-auto whitespace-pre-wrap leading-tight mt-1.5">
                                    {JSON.stringify(evt.detail, null, 2)}
                                  </pre>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="h-48 flex items-center justify-center text-center p-8 text-white/30 text-xs">
                        No run selected. Run a resolve query or inspect a ticket's audit log.
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Tickets Store Tab */}
                {activeTab === "tickets" && (
                  <motion.div key="tickets" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} className="space-y-3">
                    {tickets.length === 0 ? (
                      <div className="h-48 flex items-center justify-center text-center p-8 text-white/30 text-xs">
                        Ticket store is clean. All active cases are resolved.
                      </div>
                    ) : (
                      tickets.map((tk) => (
                        <div key={tk.ticket_id} className="p-3.5 rounded-xl border border-white/[0.06] bg-white/[0.01] hover:bg-white/[0.03] transition-all space-y-3 group relative overflow-hidden">
                          <div className="absolute top-0 right-0 w-16 h-16 bg-white/[0.01] rounded-full blur-xl" />
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-xs font-bold truncate text-white/80 group-hover:text-white transition-colors">{tk.query}</p>
                              <p className="text-[0.65rem] text-white/30 font-mono mt-0.5">#{tk.ticket_id.substring(0, 8)}</p>
                            </div>
                            <span className={`shrink-0 text-[0.65rem] px-2 py-0.5 rounded font-medium border ${
                              tk.status === "resolved" 
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/10" 
                                : "bg-red-500/10 text-red-400 border-red-500/10"
                            }`}>
                              {tk.status}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[0.68rem] bg-black/40 p-2 rounded-lg border border-white/5">
                            <div>
                              <span className="text-white/40">Category:</span>
                              <span className="font-semibold block capitalize text-white/70">{tk.issue_type}</span>
                            </div>
                            <div>
                              <span className="text-white/40">Severity:</span>
                              <span className="font-semibold block capitalize text-white/70">{tk.severity}</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 pt-1.5 justify-between">
                            <button onClick={() => loadAuditTrail(tk.ticket_id)}
                              className="text-[0.68rem] hover:text-white text-white/50 flex items-center gap-1 transition-all">
                              <Eye className="w-3 h-3" /> Inspect Logs
                            </button>
                            {tk.status !== "resolved" && (
                              <button onClick={() => resolveTicket(tk.ticket_id)}
                                className="text-[0.68rem] font-semibold text-emerald-400 hover:text-emerald-300 transition-all flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Resolve
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </motion.div>
                )}

              </AnimatePresence>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
