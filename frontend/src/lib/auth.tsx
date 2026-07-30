"use client";

import React, {
  createContext, useContext, useEffect, useState, useCallback,
} from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/utils/apiBaseUrl";

export interface User {
  user_id: string;
  email: string;
  name: string;
  org_id: string;
  role: string;
  created_at?: string;
}
export interface Org {
  org_id: string;
  name: string;
  created_at?: string;
}
export interface RegisterData {
  email: string;
  password: string;
  name: string;
  org_name: string;
}
interface AuthState {
  user: User | null;
  org: Org | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

const TOKEN_KEY = "flowclaw_token";
const AuthContext = createContext<AuthState | undefined>(undefined);

// Attach the stored token to EVERY axios request at send-time. This is robust
// against component mount-order (a page firing a request before the provider's
// effect runs still gets the token). Registered once at module load.
let _interceptorInstalled = false;
if (!_interceptorInstalled) {
  _interceptorInstalled = true;
  axios.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
      const t = localStorage.getItem(TOKEN_KEY);
      if (t) {
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${t}`;
      }
    }
    return config;
  });
}

/** Attach or clear the bearer token on the shared axios instance, so every
 *  existing axios call in the app automatically sends it — no per-call edits. */
function setAuthHeader(token: string | null) {
  if (token) {
    axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete axios.defaults.headers.common["Authorization"];
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const api = getApiBaseUrl();
  const [user, setUser] = useState<User | null>(null);
  const [org, setOrg] = useState<Org | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // On load: if a token is stored, verify it via /auth/me and hydrate state.
  useEffect(() => {
    const stored =
      typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    if (!stored) {
      
      setLoading(false);
      return;
    }
    setAuthHeader(stored);
    setToken(stored);
    axios
      .get(`${api}/auth/me`)
      .then((r) => {
        setUser(r.data.user);
        setOrg(r.data.org);
      })
      .catch(() => {
        // Token invalid/expired — clear it.
        localStorage.removeItem(TOKEN_KEY);
        setAuthHeader(null);
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, [api]);

  const persist = useCallback((t: string, u: User, o: Org | null) => {
    localStorage.setItem(TOKEN_KEY, t);
    setAuthHeader(t);
    setToken(t);
    setUser(u);
    setOrg(o);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const r = await axios.post(`${api}/auth/login`, { email, password });
      persist(r.data.access_token, r.data.user, r.data.org);
    },
    [api, persist]
  );

  const register = useCallback(
    async (data: RegisterData) => {
      const r = await axios.post(`${api}/auth/register`, data);
      persist(r.data.access_token, r.data.user, r.data.org);
    },
    [api, persist]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuthHeader(null);
    setToken(null);
    setUser(null);
    setOrg(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, org, token, loading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/** Guard hook: redirects to /login once we know the user isn't authenticated. */
export function useRequireAuth(): AuthState {
  const auth = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!auth.loading && !auth.user) {
      router.replace("/login");
    }
  }, [auth.loading, auth.user, router]);
  return auth;
}
