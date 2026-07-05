import { describe, it, expect } from "vitest";
import { toCsv } from "./csv";

describe("toCsv", () => {
  const columns = [
    { key: "symbol" as const, label: "Symbol" },
    { key: "price" as const, label: "Price" },
  ];

  it("renders header and rows", () => {
    const rows = [
      { symbol: "AAPL", price: 200.5 },
      { symbol: "MSFT", price: 400 },
    ];
    expect(toCsv(rows, columns)).toBe(
      "Symbol,Price\r\nAAPL,200.5\r\nMSFT,400"
    );
  });

  it("renders header only for empty rows", () => {
    expect(toCsv([], columns)).toBe("Symbol,Price");
  });

  it("quotes and escapes values containing commas, quotes, or newlines", () => {
    const rows = [{ symbol: "AAPL", price: 'has "quotes", a comma, and\na newline' }];
    expect(toCsv(rows, columns)).toBe(
      'Symbol,Price\r\nAAPL,"has ""quotes"", a comma, and\na newline"'
    );
  });

  it("renders null/undefined as empty string", () => {
    const rows = [{ symbol: "AAPL", price: null }, { symbol: "MSFT", price: undefined }];
    expect(toCsv(rows, columns)).toBe("Symbol,Price\r\nAAPL,\r\nMSFT,");
  });
});
