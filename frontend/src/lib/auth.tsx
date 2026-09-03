"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";
import type { RoleProfile } from "./types";

interface AuthState {
  roleKey: string | null;
  profile: RoleProfile | null;
  persona: string;
  ready: boolean;
  login: (roleKey: string) => Promise<void>;
  logout: () => void;
  setPersona: (p: string) => void;
}

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "boardmind:session";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [roleKey, setRoleKey] = useState<string | null>(null);
  const [profile, setProfile] = useState<RoleProfile | null>(null);
  const [persona, setPersonaState] = useState("ceo");
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        setRoleKey(parsed.roleKey);
        setProfile(parsed.profile);
        setPersonaState(parsed.persona || "ceo");
      } catch {
        /* corrupt/old session — ignore */
      }
    }
    setReady(true);
  }, []);

  async function login(key: string) {
    const res = await api.login(key);
    setRoleKey(res.role);
    setProfile(res.profile);
    const nextPersona = key === "finance" ? "finance" : key === "marketing" ? "marketing" : key === "regional" ? "regional" : "ceo";
    setPersonaState(nextPersona);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ roleKey: res.role, profile: res.profile, persona: nextPersona }));
    router.push("/");
  }

  function logout() {
    setRoleKey(null);
    setProfile(null);
    window.localStorage.removeItem(STORAGE_KEY);
    router.push("/login");
  }

  function setPersona(p: string) {
    setPersonaState(p);
    if (roleKey && profile) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ roleKey, profile, persona: p }));
    }
  }

  return (
    <AuthContext.Provider value={{ roleKey, profile, persona, ready, login, logout, setPersona }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
