import { describe, expect, it } from "vitest";
import { deriveCurrency, fieldsForType, validateTransaction } from "./holdings";

describe("deriveCurrency", () => {
  it("maps Taiwan suffixes to TWD, everything else to USD", () => {
    expect(deriveCurrency("2330.TW")).toBe("TWD");
    expect(deriveCurrency("6488.two")).toBe("TWD");
    expect(deriveCurrency("AAPL")).toBe("USD");
    expect(deriveCurrency(" tsla ")).toBe("USD");
  });
});

describe("fieldsForType", () => {
  it("adapts to the transaction type", () => {
    expect(fieldsForType("buy", "position")).toEqual(
      new Set(["symbol", "qty", "price", "fee"]),
    );
    expect(fieldsForType("dividend", "position")).toEqual(
      new Set(["symbol", "amount", "fee"]),
    );
    expect(fieldsForType("deposit", "position")).toEqual(new Set(["amount"]));
    expect(fieldsForType("split", "position")).toEqual(new Set(["symbol", "qty"]));
    expect(fieldsForType("adjust", "position")).toEqual(
      new Set(["symbol", "qty", "price"]),
    );
    expect(fieldsForType("adjust", "cash")).toEqual(new Set(["amount"]));
  });
});

const base = {
  type: "buy" as const, adjustVariant: "position" as const,
  tradeDate: "2026-07-01", symbol: "AAPL", qty: "10", price: "100",
  amount: "", fee: "0", currency: "USD" as const,
};

describe("validateTransaction", () => {
  it("passes a valid buy", () => {
    expect(validateTransaction(base)).toBeNull();
  });
  it("requires a trade date", () => {
    expect(validateTransaction({ ...base, tradeDate: "" }))
      .toBe("holdings.form.errors.dateRequired");
  });
  it("requires symbol and positive qty/price for buys", () => {
    expect(validateTransaction({ ...base, symbol: "" }))
      .toBe("holdings.form.errors.symbolRequired");
    expect(validateTransaction({ ...base, qty: "0" }))
      .toBe("holdings.form.errors.qtyPositive");
    expect(validateTransaction({ ...base, price: "-1" }))
      .toBe("holdings.form.errors.priceInvalid");
  });
  it("requires positive amount for deposits", () => {
    expect(validateTransaction({
      ...base, type: "deposit", amount: "0",
    })).toBe("holdings.form.errors.amountPositive");
    expect(validateTransaction({
      ...base, type: "deposit", amount: "100",
    })).toBeNull();
  });
  it("allows qty 0 for adjust-position but requires price", () => {
    expect(validateTransaction({
      ...base, type: "adjust", qty: "0", price: "0",
    })).toBeNull();
    expect(validateTransaction({
      ...base, type: "adjust", price: "",
    })).toBe("holdings.form.errors.priceInvalid");
  });
  it("requires amount for adjust-cash", () => {
    expect(validateTransaction({
      ...base, type: "adjust", adjustVariant: "cash", amount: "",
    })).toBe("holdings.form.errors.amountRequired");
  });
});