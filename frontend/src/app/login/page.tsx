"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, Loader2, Mail, Lock } from "lucide-react";
import axios from "axios";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login, user, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already signed in? Skip the form.
  useEffect(() => {
    if (!authLoading && user) router.replace("/dashboard");
  }, [authLoading, user, router]);

  const handleSubmit = async () => {
    setError(null);
    if (!email || !password) {
      setError("Enter your email and password.");
      return;
    }
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (e) {
      const msg =
        axios.isAxiosError(e) && e.response?.data?.detail
          ? String(e.response.data.detail)
          : "Something went wrong. Try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030303] text-white flex items-center justify-center relative overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 -left-24 w-96 h-96 bg-violet-600/15 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -right-24 w-96 h-96 bg-sky-600/10 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-md glass rounded-3xl p-8 border border-white/10"
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-500 to-fuchsia-400 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl tracking-tight">Highwatch</span>
        </div>

        <h1 className="text-2xl font-bold mb-1">Welcome back</h1>
        <p className="text-sm text-zinc-500 mb-6">Sign in to your workspace.</p>

        <div className="space-y-4">
          <Field icon={Mail} type="email" placeholder="you@company.com"
            value={email} onChange={setEmail} onEnter={handleSubmit} />
          <Field icon={Lock} type="password" placeholder="Password"
            value={password} onChange={setPassword} onEnter={handleSubmit} />

          {error && (
            <div className="text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-2.5">
              {error}
            </div>
          )}

          <button onClick={handleSubmit} disabled={submitting}
            className="w-full bg-white text-black font-semibold rounded-xl py-3 flex items-center justify-center gap-2 hover:bg-zinc-200 transition-colors disabled:opacity-60">
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
          </button>
        </div>

        <p className="text-sm text-zinc-500 mt-6 text-center">
          No account?{" "}
          <Link href="/register" className="text-violet-400 hover:text-violet-300 font-medium">
            Create one
          </Link>
        </p>
      </motion.div>
    </div>
  );
}

function Field({ icon: Icon, type, placeholder, value, onChange, onEnter }: {
  icon: React.ComponentType<{ className?: string }>;
  type: string; placeholder: string; value: string;
  onChange: (v: string) => void; onEnter: () => void;
}) {
  return (
    <div className="relative">
      <Icon className="w-4 h-4 text-zinc-600 absolute left-4 top-1/2 -translate-y-1/2" />
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") onEnter(); }}
        className="w-full bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-zinc-600 outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/40 transition-all"
      />
    </div>
  );
}
