"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ComponentCost {
  component: string;
  amount: string;
  percentage: number;
}

interface CostSummaryResponse {
  current_month_spend: number;
  monthly_budget: number | null;
  budget_remaining: number | null;
  projected_month_end: number | null;
  breakdown_by_component: ComponentCost[];
}

interface BudgetData {
  current_spend: number;
  monthly_budget: number;
  breakdown: ComponentCost[];
}

const COMPONENT_LABELS: Record<string, string> = {
  node: "bioAF Node",
  storage: "Storage",
  compute: "Compute",
};

export function CostBudgetWidget() {
  const [data, setData] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CostSummaryResponse>("/api/costs/summary")
      .then((res) => {
        if (res.monthly_budget != null) {
          setData({
            current_spend: res.current_month_spend,
            monthly_budget: res.monthly_budget,
            breakdown: res.breakdown_by_component || [],
          });
        }
      })
      .catch(() => setError("Failed to load budget data"))
      .finally(() => setLoading(false));
  }, []);

  const pct = data ? Math.min((data.current_spend / data.monthly_budget) * 100, 100) : 0;
  const barColor = pct > 90 ? "bg-red-500" : pct > 75 ? "bg-amber-500" : "bg-green-500";

  return (
    <div className="bg-white rounded-lg shadow p-5" data-testid="widget-cost-budget">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Cost vs. Budget
      </h3>
      {loading && (
        <div className="animate-pulse space-y-2" data-testid="widget-loading">
          <div className="h-4 bg-gray-100 rounded w-1/2" />
          <div className="h-3 bg-gray-100 rounded" />
        </div>
      )}
      {error && (
        <div className="text-sm text-red-600" data-testid="widget-error">
          {error}
          <button onClick={() => window.location.reload()} className="ml-2 text-bioaf-600 hover:underline">
            Retry
          </button>
        </div>
      )}
      {!loading && !error && !data && (
        <p className="text-sm text-gray-400" data-testid="widget-empty">
          Budget not configured. Set up in Infrastructure &gt; Cost Center.
        </p>
      )}
      {!loading && !error && data && (
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-700">
              ${data.current_spend.toLocaleString()}
            </span>
            <span className="text-gray-500">
              ${data.monthly_budget.toLocaleString()}
            </span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">{Math.round(pct)}% of monthly budget</p>

          {data.breakdown.length > 0 && (
            <div className="mt-3 space-y-1 border-t pt-2">
              {data.breakdown.map((item) => (
                <div key={item.component} className="flex justify-between text-xs text-gray-600">
                  <span>{COMPONENT_LABELS[item.component] || item.component}</span>
                  <span>${parseFloat(item.amount).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
