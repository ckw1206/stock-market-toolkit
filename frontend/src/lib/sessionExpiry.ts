import axios from "axios";

/**
 * All API modules call the default axios instance directly (no shared
 * client), so a global response interceptor is the one place that can catch
 * every expired-session 401 without touching each call site. Only requests
 * that carried a bearer token count as "session expired" — an unauthenticated
 * 401 (e.g. a bad login attempt) must not trigger this.
 */
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const hadToken = Boolean(
      (error?.config?.headers as Record<string, string> | undefined)?.Authorization
    );
    if (error?.response?.status === 401 && hadToken) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
