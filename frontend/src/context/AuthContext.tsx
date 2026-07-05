import { createContext, useState, useEffect, startTransition, type ReactNode } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "";

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("access_token"));
  const [loading, setLoading] = useState(true);

  const fetchUser = async (accessToken: string) => {
    try {
      const res = await axios.get(`${API}/api/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      startTransition(() => setUser(res.data));
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      startTransition(() => {
        setToken(null);
        setUser(null);
      });
    }
  };

  useEffect(() => {
    if (!token) {
      startTransition(() => setLoading(false));
      return;
    }
    let ignore = false;
    fetchUser(token).then(() => {
      if (!ignore) startTransition(() => setLoading(false));
    }).catch(() => {
      if (!ignore) startTransition(() => setLoading(false));
    });
    return () => { ignore = true; };
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await axios.post(`${API}/api/auth/login`, {
      email_or_username: email,
      password,
    });
    const { access_token, refresh_token } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setToken(access_token);
    // NOTE: fetchUser is NOT called here — the [token] useEffect (lines 49-61)
    // fires after setToken and is the single authoritative source of the user fetch.
    // The old code called fetchUser twice (once here, once from the effect) which
    // caused a race where the effect's setLoading(false) could be skipped via the
    // ignore flag if the login() fetch resolved first and triggered a state update
    // that cancelled the pending effect.
  };

  const register = async (email: string, username: string, password: string) => {
    await axios.post(`${API}/api/auth/register`, { email, username, password });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
  };

  // isAuthenticated is true only after fetchUser has confirmed the token is valid.
  // This prevents useWatchlist from racing the auth check on cold mount: if we
  // used !!token, isAuthenticated would be true immediately from localStorage
  // even while /api/auth/me is still in-flight — causing useWatchlist's refresh
  // effect (which depends on isAuthenticated) to fire before the auth round-trip
  // completes. On failed auth fetchUser clears the token, so isAuthenticated is
  // safely false for an invalid/expired token.
  const isAuthenticated = !!user;
  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

// useAuth is exported from hooks/useAuth.ts to satisfy react-refresh/only-export-components
