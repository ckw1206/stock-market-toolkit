import { useTranslation } from "react-i18next";
import type { StockData } from "@/types";
import { fmt, volFmt } from "@/lib/format";
import ChartCard from "@/components/common/ChartCard";

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
const CUTOFF = Date.now() - THIRTY_DAYS_MS;

export default function HistoryTable({ stock }: { stock: StockData }) {
  const { t } = useTranslation();
  const rows = stock.close
    .map((_, i) => ({
      ts: stock.timestamp[i],
      date: new Date(stock.timestamp[i]).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      open: stock.open[i],
      high: stock.high[i],
      low: stock.low[i],
      close: stock.close[i],
      volume: stock.volume[i],
    }))
    .filter((d) => Number(d.ts) >= CUTOFF)
    .reverse();

  return (
    <ChartCard title={t("common.cards.historicalData")} subtitle={t("common.cards.historicalDataSubtitle", { symbol: stock.symbol, count: rows.length })} bodyClassName="px-0">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2 font-medium">{t("common.fields.date")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("common.fields.open")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("common.fields.high")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("common.fields.low")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("common.fields.close")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("common.fields.volume")}</th>
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {rows.map((d) => (
              <tr key={d.ts} className="border-b border-border/50 last:border-0 hover:bg-secondary/40">
                <td className="px-4 py-1.5 font-sans text-muted-foreground">{d.date}</td>
                <td className="px-4 py-1.5 text-right">${fmt(d.open)}</td>
                <td className="px-4 py-1.5 text-right">${fmt(d.high)}</td>
                <td className="px-4 py-1.5 text-right">${fmt(d.low)}</td>
                <td className="px-4 py-1.5 text-right font-medium text-primary">${fmt(d.close)}</td>
                <td className="px-4 py-1.5 text-right text-muted-foreground">{volFmt(d.volume)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartCard>
  );
}
