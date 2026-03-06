"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ActivityFeedWidget } from "./ActivityFeedWidget";

interface ComponentStatus {
  name: string;
  status: string;
}

export function AdminDashboard() {
  const [experimentCount, setExperimentCount] = useState(0);
  const [monthSpend, setMonthSpend] = useState("0");
  const [budget, setBudget] = useState<string | null>(null);
  const [components, setComponents] = useState<ComponentStatus[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [experiments, costs, comps] = await Promise.all([
          api.get<{ total: number }>("/api/experiments?page_size=1"),
          api.get<{ current_month_spend: string; monthly_budget: string | null }>("/api/costs/summary").catch(() => ({ current_month_spend: "0", monthly_budget: null })),
          api.get<{ components: ComponentStatus[] }>("/api/components").catch(() => ({ components: [] })),
        ]);
        setExperimentCount(experiments.total);
        setMonthSpend(costs.current_month_spend);
        setBudget(costs.monthly_budget);
        setComponents(comps.components || []);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  const healthyCount = components.filter((c) => c.status === "healthy").length;
  const totalComponents = components.length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Total Experiments</p>
          <p className="text-2xl font-bold text-gray-900">{experimentCount}</p>
          <Link href="/experiments" className="text-xs text-bioaf-600">View all</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Month Spend</p>
          <p className="text-2xl font-bold text-gray-900">${parseFloat(monthSpend).toFixed(2)}</p>
          {budget && <p className="text-xs text-gray-500">of ${parseFloat(budget).toFixed(2)} budget</p>}
          <Link href="/admin/costs" className="text-xs text-bioaf-600">Cost center</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">System Health</p>
          <p className="text-2xl font-bold text-gray-900">{healthyCount}/{totalComponents}</p>
          <p className="text-xs text-gray-500">components healthy</p>
          <Link href="/components" className="text-xs text-bioaf-600">View components</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Quick Links</p>
          <div className="mt-2 space-y-1">
            <Link href="/admin/users" className="block text-xs text-bioaf-600">Users & Roles</Link>
            <Link href="/admin/backups" className="block text-xs text-bioaf-600">Backups</Link>
            <Link href="/admin/settings" className="block text-xs text-bioaf-600">Settings</Link>
          </div>
        </div>
      </div>
      <ActivityFeedWidget />
    </div>
  );
}
