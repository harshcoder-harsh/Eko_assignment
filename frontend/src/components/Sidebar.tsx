"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, HardDrive, MessageSquare, Settings } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Documents", href: "/dashboard#docs", icon: HardDrive },
    { name: "Chat", href: "/dashboard#chat", icon: MessageSquare },
  ];

  return (
    <motion.aside 
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-64 glass border-r border-white/5 h-full flex flex-col p-6 z-20"
    >
      <div className="flex items-center gap-3 mb-12">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center shadow-[0_0_15px_rgba(139,92,246,0.5)]">
          <span className="font-bold text-white text-sm">H</span>
        </div>
        <span className="font-bold text-xl tracking-tight">Highwatch</span>
      </div>

      <nav className="flex-1 space-y-2">
        {links.map((link) => {
          const isActive = pathname === link.href || (pathname === "/dashboard" && link.href === "/dashboard");
          return (
            <Link key={link.name} href={link.href}>
              <div className={`flex items-center gap-3 px-4 py-3 rounded-2xl transition-all ${isActive ? "bg-white/10 text-white shadow-sm" : "text-zinc-400 hover:text-white hover:bg-white/5"}`}>
                <link.icon className={`w-5 h-5 ${isActive ? "text-primary" : ""}`} />
                <span className="font-medium">{link.name}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6 border-t border-white/5">
        <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
          <h4 className="text-sm font-bold text-white mb-1">Storage</h4>
          <div className="w-full bg-black/50 h-2 rounded-full mt-3 mb-2 overflow-hidden">
            <div className="bg-gradient-to-r from-primary to-accent h-full w-[45%]" />
          </div>
          <p className="text-xs text-zinc-400">45% used of local FAISS</p>
        </div>
      </div>
    </motion.aside>
  );
}
