"use client";

import { ChatInterface } from "@/components/ChatInterface";
import { SyncPanel } from "@/components/SyncPanel";
import { DocsPanel } from "@/components/DocsPanel";
import { useState, useEffect, Suspense } from "react";
import axios from "axios";
import { Sparkles, BarChart3, LifeBuoy, Activity, LogOut } from "lucide-react";
import Link from "next/link";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

function DashboardContent() {
  const [docs, setDocs] = useState<{ id: string, name: string, status: string }[]>([]);
  // No login required — the dashboard always renders.
  const [isAuthenticated] = useState<boolean>(true);
  const { user, org, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const res = await axios.get(`${getApiBaseUrl()}/documents`);
        if (res.data && Array.isArray(res.data.documents)) {
          setDocs(res.data.documents);
        }
      } catch {
        // ignore
      }
    };

    if (isAuthenticated) {
      fetchDocs();
    }
  }, [isAuthenticated]);

  const handleSyncSuccess = (newDocs: { id: string, name: string, status: string }[]) => {
    setDocs((prev) => {
      // Prevent duplicates by checking doc.id
      const existingIds = new Set(prev.map(d => d.id));
      const uniqueNewDocs = newDocs.filter(d => !existingIds.has(d.id));
      return [...uniqueNewDocs, ...prev];
    });
  };

  const handleDocumentClick = (doc: { id: string, name: string }) => {
    // We can dispatch a custom event that ChatInterface will listen to
    window.dispatchEvent(new CustomEvent('requestDocumentSummary', { detail: { docId: doc.id, docName: doc.name } }));
  };

  if (isAuthenticated === null) {
    return <div className="flex items-center justify-center min-h-screen text-white bg-[#030303]">Verifying access...</div>;
  }

  return (
    <div className="flex h-screen w-full bg-[#030303] text-white font-sans overflow-hidden selection:bg-white selection:text-black">
      
      {/* --- PREMIUM BACKGROUND EFFECTS --- */}
      <div className="absolute inset-0 z-0 opacity-[0.03] mix-blend-overlay pointer-events-none" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[100vw] max-w-[1200px] h-[600px] bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.06),transparent_70%)] pointer-events-none z-0" />
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#8080800A_1px,transparent_1px),linear-gradient(to_bottom,#8080800A_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Left Sidebar */}
      <div className="w-[320px] shrink-0 border-r border-white/[0.08] bg-[#050505]/80 backdrop-blur-2xl flex flex-col relative z-10 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
        
        {/* App Brand Header */}
        <Link href="/" className="h-16 flex items-center px-6 border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors cursor-pointer group">
          <div className="w-7 h-7 rounded-lg bg-white flex items-center justify-center mr-3 shadow-[0_0_15px_rgba(255,255,255,0.3)] group-hover:scale-105 transition-transform">
            <Sparkles className="w-4 h-4 text-black" />
          </div>
          <span className="font-semibold tracking-wide text-[0.95rem] text-white/90 group-hover:text-white transition-colors">Highwatch RAG</span>
        </Link>

        {/* Analytics Agents link */}
        <Link href="/analytics" className="mx-5 mt-5 flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] hover:border-white/20 transition-all group">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-white/20 to-white/5 flex items-center justify-center group-hover:from-white group-hover:to-white/80 transition-all">
            <BarChart3 className="w-4 h-4 text-white/70 group-hover:text-black transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white/85">Analytics Agents</p>
            <p className="text-[0.68rem] text-white/40">Analyze CSV / Excel data</p>
          </div>
        </Link>

        {/* AI Observability link */}
        <Link href="/observability" className="mx-5 mt-3 flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] hover:border-white/20 transition-all group">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-white/20 to-white/5 flex items-center justify-center group-hover:from-white group-hover:to-white/80 transition-all">
            <Activity className="w-4 h-4 text-white/70 group-hover:text-black transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white/85">AI Observability</p>
            <p className="text-[0.68rem] text-white/40">Traces, latency &amp; cost</p>
          </div>
        </Link>

        {/* Support Agent link */}
        <Link href="/support" className="mx-5 mt-3 flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] hover:border-white/20 transition-all group">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-white/20 to-white/5 flex items-center justify-center group-hover:from-white group-hover:to-white/80 transition-all">
            <LifeBuoy className="w-4 h-4 text-white/70 group-hover:text-black transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white/85">Support Agent</p>
            <p className="text-[0.68rem] text-white/40">Hermes Escalation Claw</p>
          </div>
        </Link>

        {/* Sync Section */}
        <div className="p-5 border-b border-white/[0.06]">
          <SyncPanel onSyncSuccess={handleSyncSuccess} />
        </div>

        {/* Docs Section */}
        <div className="flex-1 flex flex-col min-h-0 p-5 pt-5">
          <h3 className="text-[0.7rem] font-semibold text-white/40 uppercase tracking-[0.15em] mb-4 pl-1">Knowledge Base</h3>
          <DocsPanel docs={docs} onDocumentClick={handleDocumentClick} />
        </div>

        {/* User footer */}
        {user && (
          <div className="border-t border-white/[0.06] p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-violet-500 to-fuchsia-400 flex items-center justify-center text-sm font-semibold text-white shrink-0">
                {(user.name || user.email || "?").charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white/90 truncate">{user.name || user.email}</p>
                <p className="text-[0.68rem] text-white/40 truncate">
                  {org?.name ? `${org.name} · ` : ""}
                  <span className="uppercase tracking-wide text-violet-300/80">{user.role}</span>
                </p>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/[0.06] transition-colors shrink-0"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>=

      {/* Right Column: Chat */}
      <div className="flex-1 relative z-10 flex flex-col min-w-0 bg-transparent">
        <ChatInterface />
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-white bg-[#030303]">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
