export type TxnType =
  | "buy" | "sell" | "dividend" | "deposit" | "withdrawal" | "split" | "adjust";
export type Currency = "USD" | "TWD";
export type AdjustVariant = "position" | "cash";
export type Field = "symbol" | "qty" | "price" | "amount" | "fee";

export function deriveCurrency(symbol: string): Currency {
  const s = symbol.trim().toUpperCase();
  return s.endsWith(".TW") || s.endsWith(".TWO") ? "TWD" : "USD";
}

const FIELDS: Record<Exclude<TxnType, "adjust">, Field[]> = {
  buy: ["symbol", "qty", "price", "fee"],
  sell: ["symbol", "qty", "price", "fee"],
  dividend: ["symbol", "amount", "fee"],
  deposit: ["amount"],
  withdrawal: ["amount"],
  split: ["symbol", "qty"],
};

export function fieldsForType(type: TxnType, adjustVariant: AdjustVariant): Set<Field> {
  if (type === "adjust") {
    return new Set(
      adjustVariant === "position" ? ["symbol", "qty", "price"] : ["amount"],
    );
  }
  return new Set(FIELDS[type]);
}

export interface TxnFormInput {
  type: TxnType;
  adjustVariant: AdjustVariant;
  tradeDate: string;
  symbol: string;
  qty: string;
  price: string;
  amount: string;
  fee: string;
  currency: Currency;
}

export function validateTransaction(f: TxnFormInput): string | null {
  if (!f.tradeDate) return "holdings.form.errors.dateRequired";
  const fields = fieldsForType(f.type, f.adjustVariant);
  if (fields.has("symbol") && !f.symbol.trim())
    return "holdings.form.errors.symbolRequired";
  if (fields.has("qty")) {
    const qty = Number(f.qty);
    const min = f.type === "adjust" ? 0 : Number.MIN_VALUE;
    if (f.qty === "" || !Number.isFinite(qty) || qty < min || (f.type !== "adjust" && qty <= 0))
      return "holdings.form.errors.qtyPositive";
  }
  if (fields.has("price")) {
    const price = Number(f.price);
    if (f.price === "" || !Number.isFinite(price) || price < 0)
      return "holdings.form.errors.priceInvalid";
  }
  if (fields.has("amount")) {
    const amount = Number(f.amount);
    if (f.amount === "" || !Number.isFinite(amount))
      return "holdings.form.errors.amountRequired";
    const mustBePositive = f.type === "deposit" || f.type === "withdrawal";
    if (mustBePositive && amount <= 0)
      return "holdings.form.errors.amountPositive";
  }
  if (fields.has("fee") && f.fee !== "" && (!Number.isFinite(Number(f.fee)) || Number(f.fee) < 0))
    return "holdings.form.errors.feeInvalid";
  return null;
}