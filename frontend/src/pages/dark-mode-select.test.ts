import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

// Use Vite's glob to read TSX source at build time.
const alertsSource = import.meta.glob<string>("./AlertsPage.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
})["./AlertsPage.tsx"]!;

const settingsSource = import.meta.glob<string>("./SettingsPage.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
})["./SettingsPage.tsx"]!;

// CSS: read directly via Node.js fs since ?raw/ ?url don't work for CSS in jsdom.
const cssPath = path.resolve(process.cwd(), "src/index.css");
const cssText = fs.readFileSync(cssPath, "utf-8");

describe("dark-mode select CSS regression guards", () => {
  it("index.css sets color-scheme: dark on .dark for native select popup", () => {
    // The .dark rule must declare color-scheme so Chromium/Edge render the
    // native <select> popup with correct dark text on dark background.
    expect(cssText).toContain("color-scheme: dark");
  });

  it("index.css sets color-scheme: light on :root for native select popup", () => {
    // color-scheme: light on :root ensures the popup flips to light text on
    // light background in light mode.
    expect(cssText).toContain("color-scheme: light");
  });

  it("AlertsPage option elements carry bg-background text-foreground classes", () => {
    // Every <option> inside a <select> must use Tailwind bg-background + text-foreground
    // so the dropdown items are legible in dark mode.
    const optionClassPattern = /<option\s+className="bg-background text-foreground"/;
    expect(optionClassPattern.test(alertsSource)).toBe(true);
  });

  it("SettingsPage option elements carry bg-background text-foreground classes", () => {
    // Same requirement as AlertsPage: timezone and other selects need the classes.
    const optionClassPattern = /<option\s+className="bg-background text-foreground"/;
    expect(optionClassPattern.test(settingsSource)).toBe(true);
  });
});