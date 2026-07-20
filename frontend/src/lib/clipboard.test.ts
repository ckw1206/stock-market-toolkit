import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { copyText } from "./clipboard";

describe("copyText", () => {
  let origClipboard: typeof navigator.clipboard | undefined;
  let origExecCommand: typeof document.execCommand | undefined;

  beforeEach(() => {
    origClipboard = navigator.clipboard;
    origExecCommand = document.execCommand;
  });

  afterEach(() => {
    if (origClipboard === undefined) {
      delete (navigator as { clipboard?: typeof navigator.clipboard }).clipboard;
    } else {
      (navigator as { clipboard: typeof navigator.clipboard }).clipboard = origClipboard;
    }
    if (origExecCommand === undefined) {
      delete (document as { execCommand?: typeof document.execCommand }).execCommand;
    } else {
      document.execCommand = origExecCommand;
    }
    vi.restoreAllMocks();
  });

  it("returns true via Clipboard API when available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    (navigator as { clipboard: { writeText: typeof writeText } }).clipboard = { writeText };
    expect(await copyText("hello")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("hello");
  });

  it("falls back to execCommand when navigator.clipboard is undefined and returns true", async () => {
    delete (navigator as { clipboard?: typeof navigator.clipboard }).clipboard;
    document.execCommand = vi.fn().mockReturnValue(true);
    expect(await copyText("fallback text")).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith("copy");
  });

  it("returns false when both paths fail rather than throwing", async () => {
    delete (navigator as { clipboard?: typeof navigator.clipboard }).clipboard;
    document.execCommand = vi.fn().mockReturnValue(false);
    await expect(copyText("will fail")).resolves.toBe(false);
  });

  it("returns false when Clipboard API rejects and execCommand also fails", async () => {
    (navigator as { clipboard: { writeText: () => Promise<never> } }).clipboard = {
      writeText: vi.fn().mockRejectedValue(new Error("denied")),
    };
    document.execCommand = vi.fn().mockReturnValue(false);
    await expect(copyText("denied")).resolves.toBe(false);
  });

  it("returns true when Clipboard API rejects but execCommand fallback succeeds", async () => {
    (navigator as { clipboard: { writeText: () => Promise<never> } }).clipboard = {
      writeText: vi.fn().mockRejectedValue(new Error("denied")),
    };
    document.execCommand = vi.fn().mockReturnValue(true);
    await expect(copyText("recovered")).resolves.toBe(true);
  });
});
