import { describe, it, expect, beforeEach } from "vitest";
import axios from "axios";
import "./sessionExpiry";

function reject401(hadToken: boolean) {
  const handler = (axios.interceptors.response as unknown as { handlers: { rejected: (e: unknown) => Promise<unknown> }[] })
    .handlers[0].rejected;
  return handler({
    response: { status: 401 },
    config: { headers: hadToken ? { Authorization: "Bearer x" } : {} },
  }).catch((e: unknown) => e);
}

describe("sessionExpiry interceptor", () => {
  // jsdom refuses real navigation, so stub location with a plain settable object.
  const location = { pathname: "/alerts", href: "" };

  beforeEach(() => {
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    location.pathname = "/alerts";
    location.href = "";
    Object.defineProperty(window, "location", { value: location, writable: true, configurable: true });
  });

  it("clears tokens and redirects to /login on a 401 that carried a bearer token", async () => {
    await reject401(true);
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(location.href).toBe("/login");
  });

  it("leaves tokens alone on a 401 with no Authorization header (e.g. bad login)", async () => {
    await reject401(false);
    expect(localStorage.getItem("access_token")).toBe("a");
    expect(location.href).toBe("");
  });
});
