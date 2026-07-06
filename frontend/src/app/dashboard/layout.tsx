"use client";

import { Loader2 } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Redirects to /login if not authenticated; shows a spinner while we check.
  const { loading, user } = useRequireAuth();

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#030303] text-white">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-600" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#030303] text-white overflow-hidden">
      <main className="flex-1 flex flex-col h-full relative z-10">
        {children}
      </main>
    </div>
  );
}

