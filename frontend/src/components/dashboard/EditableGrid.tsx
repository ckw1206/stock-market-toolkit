import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import GridLayout, { type LayoutItem, useContainerWidth } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { loadLayout, reconcileLayout, saveLayout } from "@/lib/dashboard-layout";
import ChartCard from "@/components/common/ChartCard";
import PriceChart from "./PriceChart";
import RsiChart from "./RsiChart";
import MacdChart from "./MacdChart";
import StockInfoCard from "./StockInfoCard";
import HistoryTable from "./HistoryTable";
import FundamentalsCard from "./FundamentalsCard";
import DividendCard from "./DividendCard";
import NewsCard from "./NewsCard";
import TopSignalsCard from "./TopSignalsCard";
import type { DashboardGridProps } from "./DashboardGrid";

export default function EditableGrid({ stock, indicators, info, fundamentals, dividends, news, newsLoading, active, topSignals }: DashboardGridProps) {
  const { t } = useTranslation();
  const { containerRef, width } = useContainerWidth();
  const dates = stock.timestamp.map((t) =>
    new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
  );
  const [stored, setStored] = useState<LayoutItem[]>(() => loadLayout() ?? []);

  // Optional cards only get a layout slot (and thus render in the grid) when
  // their data is present — react-grid-layout drops children without a slot.
  const extras = useMemo(() => {
    const s = new Set<string>();
    if (fundamentals) s.add("fundamentals");
    if (dividends) s.add("dividends");
    if (news) s.add("news");
    if (topSignals) s.add("topsignals");
    return s;
  }, [fundamentals, dividends, news, topSignals]);

  const layout = useMemo(() => reconcileLayout(stored, active, extras), [active, extras, stored]);

  const handleChange = useCallback((next: readonly LayoutItem[]) => {
    setStored(next as LayoutItem[]);
    saveLayout(next);
  }, []);

  return (
    <div ref={containerRef} className="w-full">
      <GridLayout
        layout={layout}
        width={width}
        gridConfig={{ cols: 12, rowHeight: 120, margin: [16, 16] as const }}
        dragConfig={{ enabled: true }}
        resizeConfig={{ enabled: true }}
        onLayoutChange={handleChange}
      >
        <div key="price" className="h-full overflow-hidden">
          <ChartCard className="h-full" title={`${stock.symbol} · ${stock.period.toUpperCase()}`} subtitle={t("common.charts.price")}>
            <PriceChart data={stock} indicators={indicators} showBB={active.has("bb")} active={active} />
          </ChartCard>
        </div>
        {active.has("rsi") && (
          <div key="rsi" className="h-full overflow-hidden">
            <ChartCard className="h-full" title="RSI (14)">
              <RsiChart dates={dates} rsi={indicators.rsi} />
            </ChartCard>
          </div>
        )}
        {active.has("macd") && (
          <div key="macd" className="h-full overflow-hidden">
            <ChartCard className="h-full" title="MACD (12, 26, 9)">
              <MacdChart dates={dates} macd={indicators.macd} signal={indicators.macd_signal} hist={indicators.macd_hist} />
            </ChartCard>
          </div>
        )}
        <div key="info" className="h-full overflow-auto">
          <StockInfoCard info={info} stock={stock} />
        </div>
        <div key="table" className="h-full overflow-auto">
          <HistoryTable stock={stock} />
        </div>
        {fundamentals && (
          <div key="fundamentals" className="h-full overflow-auto">
            <FundamentalsCard data={fundamentals} />
          </div>
        )}
        {dividends && (
          <div key="dividends" className="h-full overflow-auto">
            <DividendCard data={dividends} />
          </div>
        )}
        {news && (
          <div key="news" className="h-full overflow-auto">
            <NewsCard news={news} loading={newsLoading} />
          </div>
        )}
        {topSignals && (
          <div key="topsignals" className="h-full overflow-auto">
            <TopSignalsCard />
          </div>
        )}
      </GridLayout>
    </div>
  );
}
