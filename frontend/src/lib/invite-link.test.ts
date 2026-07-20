import { describe, it, expect } from "vitest";
import { absoluteInviteLink } from "./invite-link";

describe("absoluteInviteLink", () => {
  it("passes through absolute https URLs", () => {
    expect(absoluteInviteLink("https://app.example.com/register?token=abc")).toBe("https://app.example.com/register?token=abc");
  });
  it("passes through absolute http URLs", () => {
    expect(absoluteInviteLink("http://localhost:3000/register?token=abc")).toBe("http://localhost:3000/register?token=abc");
  });
  it("passes through protocol-relative URLs", () => {
    expect(absoluteInviteLink("//cdn.example.com/register?token=abc")).toBe("//cdn.example.com/register?token=abc");
  });
  it("prefixes root-relative paths with window.location.origin", () => {
    expect(absoluteInviteLink("/register?token=abc")).toBe("http://localhost:3000/register?token=abc");
  });
  it("leaves a bare invite code untouched", () => {
    expect(absoluteInviteLink("abc123xyz")).toBe("abc123xyz");
  });
  it("leaves an empty string untouched", () => {
    expect(absoluteInviteLink("")).toBe("");
  });
});
