import { useTranslation } from "react-i18next";
import type { StockData, Indicators, StockInfo, Fundamentals, DividendData, NewsData } from "@/types";
import type { TopSignalsData } from "@/api/stockApi";
import ChartCard from "@/components/common/ChartCard";
import PriceChart from "./PriceChart";
import RsiChart from "./RsiChart";
import MacdChart from "./MacdChart";
import StockInfoCard from "./StockInfoCard";
import HistoryTable from "./HistoryTable";
import FundamentalsCard from "./FundamentalsCard";
import DividendCard from "./DividendCard";
import WatchlistButton from "@/components/common/WatchlistButton";
import NewsCard from "./NewsCard";
import TopSignalsStrip from "./TopSignalsStrip";
import HeatmapCard from "./HeatmapCard";
import PositionSizeCard from "./PositionSizeCard";
import BreadthCard from "./BreadthCard";

export interface DashboardGridProps {
  stock: StockData;
  indicators: Indicators;
  info: StockInfo;
  fundamentals: Fundamentals | null;
  dividends: DividendData | null;
  news: NewsData | null;
  newsLoading: boolean;
  active: Set<string>;
  topSignals?: TopSignalsData | null;
}

// Fluid overview layout: card rows use auto-fit grids / flex-wrap so column
// count adapts to width with no hardcoded breakpoints. See the design handoff.
const AUTO_FIT = "grid gap-4 grid-cols-[repeat(auto-fit,minmax(260px,1fr))]";

export default function DashboardGrid({ stock, indicators, info, fundamentals, dividends, news, newsLoading, active }: DashboardGridProps) {
  const { t } = useTranslation();
  const dates = stock.timestamp.map((ts) =>
    new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
  );
  const showRsi = active.has("rsi");
  const showMacd = active.has("macd");

  return (
    <div className="flex flex-col gap-4">
      <TopSignalsStrip />

      <ChartCard title={`${stock.symbol} · ${stock.period.toUpperCase()}`} subtitle={t("common.charts.price")} toolbar={<WatchlistButton symbol={stock.symbol} />}>
        <PriceChart data={stock} indicators={indicators} showBB={active.has("bb")} active={active} />
      </ChartCard>

      {(showRsi || showMacd) && (
        <div className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(320px,1fr))]">
          {showRsi && (
            <ChartCard title="RSI (14)">
              <RsiChart dates={dates} rsi={indicators.rsi} />
            </ChartCard>
          )}
          {showMacd && (
            <ChartCard title="MACD (12, 26, 9)">
              <MacdChart dates={dates} macd={indicators.macd} signal={indicators.macd_signal} hist={indicators.macd_hist} />
            </ChartCard>
          )}
        </div>
      )}

      {/* Stock info + capped-height history table, kept the same height so a
          long row list never stretches the row taller than its neighbor. */}
      <div className="flex flex-wrap items-stretch gap-4">
        <div className="min-w-0 flex-[1_1_320px]">
          <StockInfoCard info={info} stock={stock} className="h-[460px] overflow-y-auto" />
        </div>
        <div className="min-w-0 flex-[2_1_480px]">
          <HistoryTable stock={stock} capped />
        </div>
      </div>

      {(fundamentals || dividends || news) && (
        <div className={AUTO_FIT}>
          {fundamentals && <FundamentalsCard data={fundamentals} />}
          {dividends && <DividendCard data={dividends} />}
          {news && <NewsCard news={news} loading={newsLoading} />}
        </div>
      )}

      <div className={AUTO_FIT}>
        <HeatmapCard />
        <PositionSizeCard symbol={stock.symbol} />
        <BreadthCard />
      </div>
    </div>
  );
}
