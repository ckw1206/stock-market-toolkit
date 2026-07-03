// Single source of truth for the displayed app version.
//
// At build time Vite injects VITE_APP_VERSION (set by the Docker build-arg in
// CI from the release tag — see frontend/Dockerfile + .github/workflows/docker.yml).
// The fallback below is used only when the env var is absent (e.g. local `vite
// dev`) and is bumped automatically by release-please (release-please-config.json
// extra-files) so it never drifts behind the released version.
// CI injects the release tag verbatim (e.g. "v0.9.2"), but the value is meant to
// be a bare semver — the "v" prefix is added below when building URLs. Strip any
// leading "v" so the prefix isn't doubled (which produced dead "vv0.9.2" links).
export const normalizeVersion = (v: string): string => v.replace(/^v/, "");

export const APP_VERSION = normalizeVersion(
  (import.meta.env.VITE_APP_VERSION as string) || "0.13.0", // x-release-please-version
);

// Centralized release page URL — used by Navbar and Footer
export const RELEASE_URL = `https://github.com/ai-workflow-space/stock-market-toolkit/releases/tag/v${APP_VERSION}`;

// GitHub Releases API endpoint for the current version's tag
export const RELEASE_API_URL = `https://api.github.com/repos/ai-workflow-space/stock-market-toolkit/releases/tags/v${APP_VERSION}`;
