import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { getStockInfo, clearTickerCache } from "./stockApi";

vi.mock("axios");

describe("ticker data cache", () => {
  beforeEach(() => {
    clearTickerCache();
    vi.mocked(axios.get).mockReset();
    vi.mocked(axios.get).mockResolvedValue({ data: { symbol: "AAPL" } });
  });

  it("reuses a cached response instead of re-fetching", async () => {
    await getStockInfo("AAPL");
    await getStockInfo("AAPL");
    expect(axios.get).toHaveBeenCalledTimes(1);
  });

  it("dedupes concurrent requests for the same key", async () => {
    await Promise.all([getStockInfo("AAPL"), getStockInfo("aapl")]);
    expect(axios.get).toHaveBeenCalledTimes(1);
  });

  it("does not cache failures", async () => {
    vi.mocked(axios.get).mockRejectedValueOnce(new Error("boom"));
    await expect(getStockInfo("AAPL")).rejects.toThrow("boom");
    await getStockInfo("AAPL");
    expect(axios.get).toHaveBeenCalledTimes(2);
  });

  it("clearTickerCache forces a re-fetch", async () => {
    await getStockInfo("AAPL");
    clearTickerCache();
    await getStockInfo("AAPL");
    expect(axios.get).toHaveBeenCalledTimes(2);
  });
});
