"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Database, Search, Zap, Sparkles } from "lucide-react";
import { useState, useEffect, Suspense } from "react";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 30, filter: "blur(10px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 100, damping: 20, mass: 1 }
  }
};

const pulseVariants = {
  hidden: { opacity: 0.4, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 3,
      repeat: Infinity,
      repeatType: "reverse" as const,
      ease: "easeInOut"
    }
  }
};

// Animated flowing lines background component
function FlowingLines() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 opacity-30">
      <svg className="absolute w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        <motion.path
          d="M0,50 Q25,20 50,50 T100,50"
          fill="none"
          stroke="rgba(255, 255, 255, 0.15)"
          strokeWidth="0.5"
          initial={{ pathLength: 0, pathOffset: 0 }}
          animate={{ pathLength: 1, pathOffset: 1 }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
        />
        <motion.path
          d="M0,60 Q30,90 60,60 T100,60"
          fill="none"
          stroke="rgba(255, 255, 255, 0.1)"
          strokeWidth="0.3"
          initial={{ pathLength: 0, pathOffset: 0 }}
          animate={{ pathLength: 1, pathOffset: 1 }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear", delay: 2 }}
        />
        <motion.path
          d="M0,40 Q40,10 70,40 T100,40"
          fill="none"
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="0.2"
          initial={{ pathLength: 0, pathOffset: 0 }}
          animate={{ pathLength: 1, pathOffset: 1 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear", delay: 5 }}
        />
      </svg>
    </div>
  );
}

// Floating particles component
function FloatingParticles() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {[...Array(20)].map((_, i) => {
        const size = Math.random() * 4 + 1;
        return (
          <motion.div
            key={i}
            className="absolute rounded-full bg-white"
            style={{
              width: size,
              height: size,
              top: `${Math.random() * 100}%`,
              left: `${Math.random() * 100}%`,
              opacity: Math.random() * 0.3 + 0.1,
            }}
            animate={{
              y: [0, -Math.random() * 100 - 50],
              x: [0, (Math.random() - 0.5) * 50],
              opacity: [0, Math.random() * 0.5 + 0.2, 0],
            }}
            transition={{
              duration: Math.random() * 10 + 10,
              repeat: Infinity,
              ease: "linear",
              delay: Math.random() * 10,
            }}
          />
        );
      })}
    </div>
  );
}

// Advanced Shooting Stars Component
function ShootingStars() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 [mask-image:linear-gradient(to_bottom,black,transparent)]">
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={`star-${i}`}
          className="absolute h-[1px] w-[150px] bg-gradient-to-r from-transparent via-white to-transparent opacity-0"
          style={{
            top: `${Math.random() * 60 - 10}%`,
            left: `${Math.random() * 100}%`,
            transform: 'rotate(-35deg)',
            filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.8))'
          }}
          animate={{
            x: [0, -600],
            y: [0, 600],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: Math.random() * 1.5 + 1.5,
            repeat: Infinity,
            repeatDelay: Math.random() * 4 + 2,
            ease: "linear",
            delay: Math.random() * 5,
          }}
        />
      ))}
    </div>
  );
}

// Glowing Pulse Nodes
function PulseNodes() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={`node-${i}`}
          className="absolute w-2 h-2 rounded-full bg-white"
          style={{
            top: `${Math.random() * 80 + 10}%`,
            left: `${Math.random() * 80 + 10}%`,
            boxShadow: '0 0 20px 2px rgba(255,255,255,0.4)',
          }}
          animate={{
            scale: [1, 2, 1],
            opacity: [0.1, 0.6, 0.1],
          }}
          transition={{
            duration: Math.random() * 3 + 2,
            repeat: Infinity,
            ease: "easeInOut",
            delay: Math.random() * 2,
          }}
        >
          {/* Connecting line to nowhere for tech feel */}
          <motion.div 
            className="absolute top-1/2 left-1/2 h-[1px] w-[100px] bg-gradient-to-r from-white/30 to-transparent origin-left"
            style={{ rotate: `${Math.random() * 360}deg` }}
            animate={{ opacity: [0, 0.5, 0] }}
            transition={{
              duration: Math.random() * 4 + 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: Math.random() * 2,
            }}
          />
        </motion.div>
      ))}
    </div>
  );
}

// Ambient Aurora Background Component
function AmbientAurora() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      <motion.div
        className="absolute top-[-20%] left-[-10%] w-[60vw] h-[60vh] rounded-full mix-blend-screen filter blur-[150px] opacity-[0.03] bg-white"
        animate={{
          x: [0, 100, 0],
          y: [0, 50, 0],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      <motion.div
        className="absolute bottom-[-20%] right-[-10%] w-[70vw] h-[70vh] rounded-full mix-blend-screen filter blur-[150px] opacity-[0.02] bg-white"
        animate={{
          x: [0, -100, 0],
          y: [0, -50, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 2,
        }}
      />
    </div>
  );
}

function HomeContent() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <main className="min-h-screen relative bg-[#030303] overflow-x-hidden flex flex-col items-center justify-center pt-24 pb-12 px-6 text-center text-white selection:bg-white selection:text-black font-sans">
      
      {/* --- PREMIUM BACKGROUND EFFECTS --- */}
      
      {/* Noise Texture Overlay for Cinematic Feel */}
      <div className="absolute inset-0 z-0 opacity-[0.06] mix-blend-overlay pointer-events-none" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      
      {/* Top Spotlight Glow */}
      <motion.div 
        variants={pulseVariants}
        initial="hidden"
        animate="visible"
        className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[100vw] max-w-[1200px] h-[600px] bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.08),transparent_70%)] pointer-events-none z-0" 
      />

      {/* Bottom Soft Glow */}
      <motion.div 
        variants={pulseVariants}
        initial="hidden"
        animate="visible"
        style={{ animationDelay: '1.5s' }}
        className="absolute bottom-[-20%] left-1/2 -translate-x-1/2 w-[80vw] h-[400px] bg-[radial-gradient(ellipse_at_bottom,rgba(255,255,255,0.05),transparent_70%)] pointer-events-none z-0" 
      />

      {/* Subtle Grid */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#8080800A_1px,transparent_1px),linear-gradient(to_bottom,#8080800A_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Persistent Animations */}
      <AmbientAurora />
      <FlowingLines />
      <FloatingParticles />
      <PulseNodes />
      <ShootingStars />

      {/* --- CONTENT --- */}
      
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 w-full max-w-5xl mx-auto flex flex-col items-center"
      >
        
        {/* Animated Badge */}
        <motion.div 
          variants={itemVariants}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/10 backdrop-blur-xl mb-10 shadow-[0_0_20px_rgba(255,255,255,0.03)]"
        >
          <Sparkles className="w-3.5 h-3.5 text-white/70" />
          <span className="text-xs font-semibold tracking-[0.2em] uppercase text-white/70">
            FlowClaw Engine (LLaMA 3.3 70B)
          </span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1 
          variants={itemVariants}
          className="text-5xl sm:text-7xl md:text-[6.5rem] font-medium tracking-[-0.04em] mb-8 leading-[0.95] text-white relative"
        >
          {/* Subtle text glow effect behind the title */}
          <div className="absolute inset-0 blur-3xl opacity-20 bg-white z-[-1] rounded-[100%]" />
          Autonomous AI agents <br className="hidden sm:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-b from-white via-white/90 to-white/40 drop-shadow-[0_0_40px_rgba(255,255,255,0.15)] relative inline-block">
            for your workflows.
            <motion.span 
              className="absolute -right-8 -top-4"
              animate={{ rotate: [0, 10, 0, -10, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
            >
              <Sparkles className="w-8 h-8 text-white/50" />
            </motion.span>
          </span>
        </motion.h1>
        
        {/* Hero Description */}
        <motion.p 
          variants={itemVariants}
          className="text-lg md:text-xl text-white/50 mb-12 max-w-2xl mx-auto leading-[1.7] font-normal tracking-wide"
        >
          Document Q&amp;A, analytics agents, and a support-escalation claw — with full observability and audit trails. Multi-tenant, grounded, and built to be inspected.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          variants={itemVariants}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 w-full sm:w-auto"
        >
          <Link
            href="/dashboard"
            className="group relative flex items-center justify-center gap-3 bg-white text-black px-8 py-3.5 rounded-full font-medium text-base overflow-hidden transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] w-full sm:w-auto shadow-[0_0_40px_rgba(255,255,255,0.15)] hover:shadow-[0_0_60px_rgba(255,255,255,0.3)]"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-black/[0.05] to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
            <Sparkles className="w-4 h-4" />
            <span>Open Chat & Documents</span>
          </Link>

          <Link
            href="/analytics"
            className="group flex items-center justify-center gap-2 bg-white/[0.03] text-white border border-white/10 px-8 py-3.5 rounded-full font-medium text-base transition-all duration-300 hover:bg-white/5 hover:border-white/20 w-full sm:w-auto"
          >
            <span>Analytics Agents</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
          </Link>
        </motion.div>
      </motion.div>

      {/* --- FEATURES GRID --- */}
      
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto mt-32 relative z-10 w-full px-4"
      >
        {[
          { icon: Database, title: "Instant Upload", desc: "Drop in PDFs, Docs, TXT, CSV or Excel — or paste a direct link — and start in seconds. No login." },
          { icon: Zap, title: "LLaMA 3.3 (70B)", desc: "Powered by Groq's LPU inference engine for lightning-fast, high-quality responses." },
          { icon: Search, title: "Vector Precision", desc: "FAISS vector search ensures the AI always finds the exact paragraph you need." },
        ].map((feature, idx) => (
          <motion.div 
            key={idx}
            variants={itemVariants}
            className="group relative rounded-[2rem] border border-white/[0.08] bg-[#0A0A0A] p-10 text-left overflow-hidden backdrop-blur-md transition-all duration-500 hover:bg-white/[0.02] hover:-translate-y-1 hover:border-white/20 hover:shadow-[0_20px_40px_rgba(0,0,0,0.4)]"
          >
            {/* Subtle inner hover glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.05] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
            
            <div className="w-12 h-12 rounded-xl border border-white/10 bg-white/[0.05] flex items-center justify-center mb-6 transition-transform duration-500 group-hover:scale-110 group-hover:bg-white group-hover:text-black text-white/70 shadow-inner">
              <feature.icon className="w-5 h-5 transition-colors duration-500" />
            </div>
            
            <h3 className="text-xl font-semibold mb-3 text-white/90 tracking-tight">{feature.title}</h3>
            <p className="text-white/50 leading-relaxed text-base font-normal">{feature.desc}</p>
          </motion.div>
        ))}
      </motion.div>
      
      {/* Footer with Privacy & Terms */}
      <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-6 text-xs text-white/30 z-20">
        <Link href="/privacy" className="hover:text-white/70 transition-colors">
          Privacy Policy
        </Link>
        <Link href="/terms" className="hover:text-white/70 transition-colors">
          Terms of Service
        </Link>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-white bg-zinc-950">Loading...</div>}>
      <HomeContent />
    </Suspense>
  );
}
