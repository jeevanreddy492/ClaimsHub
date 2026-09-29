import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, loadSession, saveSession, setUnauthorizedHandler } from "../api/client";
import type { Role, Session } from "../api/types";

interface AuthState {
  session: Session | null;
  role: Role | undefined;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => loadSession());

  const logout = useCallback(() => {
    saveSession(null);
    setSession(null);
  }, []);

  useEffect(() => setUnauthorizedHandler(logout), [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api<Omit<Session, "expires_at"> & { expires_in: number }>("/auth/login", {
      method: "POST",
      body: { username, password },
    });
    const s: Session = {
      access_token: res.access_token,
      username: res.username,
      role: res.role,
      full_name: res.full_name,
      expires_at: Date.now() + res.expires_in * 1000,
    };
    saveSession(s);
    setSession(s);
  }, []);

  const value = useMemo(() => ({ session, role: session?.role, login, logout }), [session, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
