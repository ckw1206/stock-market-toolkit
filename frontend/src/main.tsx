import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import App from "./App.tsx";
import "./index.css";
import "./i18n/index.ts";
import "./lib/sessionExpiry.ts";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
