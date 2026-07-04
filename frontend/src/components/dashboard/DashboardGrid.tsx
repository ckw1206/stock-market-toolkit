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
import TopSignalsCard from "./TopSignalsCard";
import HeatmapCard from "./HeatmapCard";
import PositionSizeCard from "./PositionSizeCard";

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

export default function DashboardGrid({ stock, indicators, info, fundamentals, dividends, news, newsLoading, active, topSignals }: DashboardGridProps) {
  const { t } = useTranslation();
  const dates = stock.timestamp.map((ts) =>
    new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
  );
  const showRsi = active.has("rsi");
  const showMacd = active.has("macd");

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12">
        <ChartCard title={`${stock.symbol} · ${stock.period.toUpperCase()}`} subtitle={t("common.charts.price")} toolbar={<WatchlistButton symbol={stock.symbol} />}>
          <PriceChart data={stock} indicators={indicators} showBB={active.has("bb")} active={active} />
        </ChartCard>
      </div>

      {showRsi && (
        <div className="col-span-12 lg:col-span-6">
          <ChartCard title="RSI (14)">
            <RsiChart dates={dates} rsi={indicators.rsi} />
          </ChartCard>
        </div>
      )}

      {showMacd && (
        <div className="col-span-12 lg:col-span-6">
          <ChartCard title="MACD (12, 26, 9)">
            <MacdChart dates={dates} macd={indicators.macd} signal={indicators.macd_signal} hist={indicators.macd_hist} />
          </ChartCard>
        </div>
      )}

      <div className="col-span-12 lg:col-span-4">
        <StockInfoCard info={info} stock={stock} />
      </div>

      <div className="col-span-12 lg:col-span-8">
        <HistoryTable stock={stock} />
      </div>

      {fundamentals && (
        <div className="col-span-12 lg:col-span-4">
          <FundamentalsCard data={fundamentals} />
        </div>
      )}

      {dividends && (
        <div className="col-span-12 lg:col-span-4">
          <DividendCard data={dividends} />
        </div>
      )}

      {news && (
        <div className="col-span-12 lg:col-span-4">
          <NewsCard news={news} loading={newsLoading} />
        </div>
      )}

      {topSignals && (
        <div className="col-span-12 lg:col-span-6">
          <TopSignalsCard />
        </div>
      )}
      <div className="col-span-12 lg:col-span-6">
        <HeatmapCard />
      </div>

      <div className="col-span-12 lg:col-span-4">
        <PositionSizeCard symbol={stock.symbol} />
      </div>
    </div>
  );
}
