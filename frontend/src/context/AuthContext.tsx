import { createContext, useState, useEffect, startTransition, type ReactNode } from "react";
import axios from "axios";
import { preloadTickers, clearTickerCache } from "../api/stockApi";

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
      // Fire-and-forget: warm the ticker cache for the watchlist so pages
      // open with data already loaded (runs on login and session restore).
      void preloadTickers();
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
    await fetchUser(access_token);
  };

  const register = async (email: string, username: string, password: string) => {
    await axios.post(`${API}/api/auth/register`, { email, username, password });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    clearTickerCache();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, isAuthenticated: !!user || !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

// useAuth is exported from hooks/useAuth.ts to satisfy react-refresh/only-export-components
