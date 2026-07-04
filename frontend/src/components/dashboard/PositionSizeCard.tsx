import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Calculator } from "lucide-react";
import { getPositionSize, type PositionSizePlan } from "@/api/stockApi";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

interface PositionSizeCardProps {
  symbol: string;
  className?: string;
}

const STORAGE_KEY = "stock-toolkit-position-size-inputs";

interface StoredInputs {
  account: number;
  riskPct: number;
  atrMult: number;
}

function loadInputs(): StoredInputs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { account: 10000, riskPct: 1, atrMult: 2 };
    const parsed = JSON.parse(raw);
    return {
      account: Number(parsed.account) || 10000,
      riskPct: Number(parsed.riskPct) || 1,
      atrMult: Number(parsed.atrMult) || 2,
    };
  } catch {
    return { account: 10000, riskPct: 1, atrMult: 2 };
  }
}

function saveInputs(inputs: StoredInputs): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
  } catch {
    /* ignore quota / serialization errors */
  }
}

export default function PositionSizeCard({ symbol, className }: PositionSizeCardProps) {
  const { t } = useTranslation();
  const initial = loadInputs();
  const [account, setAccount] = useState(initial.account);
  const [riskPct, setRiskPct] = useState(initial.riskPct);
  const [atrMult, setAtrMult] = useState(initial.atrMult);
  const [plan, setPlan] = useState<PositionSizePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlan = async () => {
    if (account <= 0 || riskPct <= 0 || riskPct > 100 || atrMult <= 0) {
      setError(t("dashboard.positionSize.invalidInputs"));
      return;
    }
    setLoading(true);
    setError(null);
    saveInputs({ account, riskPct, atrMult });
    try {
      const result = await getPositionSize(symbol, account, riskPct, atrMult);
      setPlan(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("dashboard.failedToLoad"));
      setPlan(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- non-critical state update for data fetch
    fetchPlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only refetch when the viewed symbol changes; inputs are applied via the Calculate button
  }, [symbol]);

  return (
    <Card className={className}>
      <CardHeader className="px-4 pb-3 pt-4">
        <div className="flex items-center gap-2">
          <Calculator className="size-4 text-muted-foreground" />
          <div className="text-sm font-medium">{t("dashboard.positionSize.title")}</div>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label htmlFor="ps-account" className="text-xs text-muted-foreground">
              {t("dashboard.positionSize.account")}
            </Label>
            <Input
              id="ps-account"
              type="number"
              min={1}
              value={account}
              onChange={(e) => setAccount(Number(e.target.value))}
              className="h-8 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="ps-risk" className="text-xs text-muted-foreground">
              {t("dashboard.positionSize.riskPct")}
            </Label>
            <Input
              id="ps-risk"
              type="number"
              min={0.1}
              max={100}
              step={0.1}
              value={riskPct}
              onChange={(e) => setRiskPct(Number(e.target.value))}
              className="h-8 text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="ps-atr" className="text-xs text-muted-foreground">
              {t("dashboard.positionSize.atrMult")}
            </Label>
            <Input
              id="ps-atr"
              type="number"
              min={0.1}
              step={0.1}
              value={atrMult}
              onChange={(e) => setAtrMult(Number(e.target.value))}
              className="h-8 text-sm"
            />
          </div>
        </div>

        <Button size="sm" className="mt-3 w-full" onClick={fetchPlan} disabled={loading}>
          {t("dashboard.positionSize.calculate")}
        </Button>

        {loading && (
          <div className="mt-3 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        )}

        {!loading && error && (
          <p className="mt-3 text-center text-sm text-muted-foreground">{error}</p>
        )}

        {!loading && !error && plan && (
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-muted-foreground">{t("dashboard.positionSize.entry")}</dt>
            <dd className="text-right font-mono tabular-nums">{plan.entry.toFixed(2)}</dd>

            <dt className="text-muted-foreground">{t("dashboard.positionSize.stop")}</dt>
            <dd className="text-right font-mono tabular-nums text-down">
              {plan.stop != null ? plan.stop.toFixed(2) : "—"}
            </dd>

            <dt className="text-muted-foreground">{t("dashboard.positionSize.shares")}</dt>
            <dd className="text-right font-mono tabular-nums font-semibold">{plan.shares}</dd>

            <dt className="text-muted-foreground">{t("dashboard.positionSize.riskAmount")}</dt>
            <dd className="text-right font-mono tabular-nums">{plan.risk_amount.toFixed(2)}</dd>

            <dt className="text-muted-foreground">{t("dashboard.positionSize.takeProfit2r")}</dt>
            <dd className="text-right font-mono tabular-nums text-up">
              {plan.take_profit_2r != null ? plan.take_profit_2r.toFixed(2) : "—"}
            </dd>

            <dt className="text-muted-foreground">{t("dashboard.positionSize.takeProfit3r")}</dt>
            <dd className="text-right font-mono tabular-nums text-up">
              {plan.take_profit_3r != null ? plan.take_profit_3r.toFixed(2) : "—"}
            </dd>
          </dl>
        )}

        {!loading && !error && plan && plan.shares === 0 && (
          <p className="mt-2 text-xs text-muted-foreground">{t("dashboard.positionSize.zeroShares")}</p>
        )}
      </CardContent>
    </Card>
  );
}
