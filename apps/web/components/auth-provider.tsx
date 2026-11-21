"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, setCsrfToken } from "../lib/api";
import type { User } from "../lib/types";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; user: User };

type Session = { user: User; csrf_token: string };

type AuthContextValue = {
  state: AuthState;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    api.get<Session>("/auth/me").then(
      (session) => {
        if (!active) return;
        setCsrfToken(session.csrf_token);
        setState({ status: "authenticated", user: session.user });
      },
      () => {
        if (active) setState({ status: "anonymous" });
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await api.post<Session>("/auth/login", { email, password });
    setCsrfToken(session.csrf_token);
    setState({ status: "authenticated", user: session.user });
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // The local state is cleared either way; an expired session is already signed out.
    }
    setCsrfToken(null);
    setState({ status: "anonymous" });
  }, []);

  const value = useMemo(() => ({ state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
