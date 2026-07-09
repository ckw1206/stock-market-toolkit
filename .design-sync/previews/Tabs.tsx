import { Tabs, TabsList, TabsTrigger, TabsContent } from "frontend";

export const Default = () => (
  <div className="bg-background text-foreground p-6">
    <Tabs defaultValue="overview" className="w-[380px]">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="technicals">Technicals</TabsTrigger>
        <TabsTrigger value="news">News</TabsTrigger>
      </TabsList>
      <TabsContent value="overview" className="pt-3 text-sm text-muted-foreground">
        Apple Inc. trades at $232.14, up 1.49% today with a market cap of $3.6T.
      </TabsContent>
      <TabsContent value="technicals" className="pt-3 text-sm text-muted-foreground">
        RSI 61.2 · MACD bullish crossover · price above 50-day SMA.
      </TabsContent>
    </Tabs>
  </div>
);
