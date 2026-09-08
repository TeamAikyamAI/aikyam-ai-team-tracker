import * as React from "react";
import { api, getStoredToken, registerUnauthorizedHandler, setStoredToken } from "@/lib/api";
import type { LoginPayload, User } from "@/types";
import { queryClient } from "@/lib/queryClient";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  status: "loading" | "authenticated" | "unauthenticated";
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [token, setToken] = React.useState<string | null>(() => getStoredToken());
  const [status, setStatus] = React.useState<"loading" | "authenticated" | "unauthenticated">(
    token ? "loading" : "unauthenticated"
  );

  const logout = React.useCallback(() => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setStatus("unauthenticated");
    queryClient.clear();
  }, []);

  React.useEffect(() => {
    registerUnauthorizedHandler(() => {
      setToken(null);
      setUser(null);
      setStatus("unauthenticated");
      queryClient.clear();
    });
  }, []);

  const fetchMe = React.useCallback(async () => {
    const { data } = await api.get<User>("/auth/me");
    setUser(data);
    setStatus("authenticated");
  }, []);

  React.useEffect(() => {
    if (!token) {
      setStatus("unauthenticated");
      return;
    }
    fetchMe().catch(() => {
      setStoredToken(null);
      setToken(null);
      setUser(null);
      setStatus("unauthenticated");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = React.useCallback(async (payload: LoginPayload) => {
    const { data } = await api.post<{ access_token: string; token_type: string }>("/auth/login", payload);
    setStoredToken(data.access_token);
    setToken(data.access_token);
    const me = await api.get<User>("/auth/me", {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    setUser(me.data);
    setStatus("authenticated");
  }, []);

  const value: AuthContextValue = {
    user,
    token,
    status,
    login,
    logout,
    refreshUser: fetchMe,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
