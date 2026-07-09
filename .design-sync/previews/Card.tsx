import {
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Button, Badge,
} from "frontend";

const Surface = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-background text-foreground p-6">{children}</div>
);

export const Basic = () => (
  <Surface>
    <Card className="max-w-sm">
      <CardHeader>
        <CardTitle>AAPL · Apple Inc.</CardTitle>
        <CardDescription>NASDAQ · Technology</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="font-mono text-2xl font-semibold tabular-nums">$232.14</div>
        <div className="mt-1 font-mono text-sm text-up tabular-nums">+3.42 (+1.49%)</div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button size="sm">Analyze</Button>
        <Button size="sm" variant="outline">Add to watchlist</Button>
      </CardFooter>
    </Card>
  </Surface>
);

export const WithBadge = () => (
  <Surface>
    <Card className="max-w-sm">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="space-y-1.5">
          <CardTitle>RSI Divergence</CardTitle>
          <CardDescription>Momentum signal · 4h</CardDescription>
        </div>
        <Badge className="bg-up text-up-foreground border-transparent">Bullish</Badge>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Price made a lower low while RSI made a higher low — a classic bullish
        reversal setup confirmed on the 4-hour timeframe.
      </CardContent>
    </Card>
  </Surface>
);
