import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { useAuth } from "./hooks/useAuth";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import BootstrapPage from "./pages/BootstrapPage";
import AdminInvitePage from "./pages/AdminInvitePage";
import LogsPage from "./pages/LogsPage";
import DashboardPage from "./pages/DashboardPage";
import SignalsPage from "./pages/SignalsPage";
import ScreenerPage from "./pages/ScreenerPage";
import PortfolioPage from "./pages/PortfolioPage";
import WatchlistPage from "./pages/WatchlistPage";
import ComparePage from "./pages/ComparePage";
import AlertsPage from "./pages/AlertsPage";
import SettingsPage from "./pages/SettingsPage";
import StyleGuidePage from "./pages/StyleGuidePage";
import "./index.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function Protected({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <TooltipProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/bootstrap" element={<BootstrapPage />} />
              <Route path="/" element={<Protected><DashboardPage /></Protected>} />
              <Route path="/signals" element={<Protected><SignalsPage /></Protected>} />
              <Route path="/screener" element={<Protected><ScreenerPage /></Protected>} />
              <Route path="/portfolio" element={<Protected><PortfolioPage /></Protected>} />
              <Route path="/watchlist" element={<Protected><WatchlistPage /></Protected>} />
              <Route path="/compare" element={<Protected><ComparePage /></Protected>} />
              <Route path="/alerts" element={<Protected><AlertsPage /></Protected>} />
              <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
              <Route path="/styleguide" element={<Protected><StyleGuidePage /></Protected>} />
              <Route path="/admin/invites" element={<Protected><AdminInvitePage /></Protected>} />
              <Route path="/admin/logs" element={<Protected><LogsPage /></Protected>} />
            </Routes>
            <Toaster />
          </TooltipProvider>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
