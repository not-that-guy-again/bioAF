"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { SystemHealth } from "@/components/dashboard/SystemHealth";
import { ComponentInventory } from "@/components/dashboard/ComponentInventory";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { HealthStatus, ComponentState, Experiment, ExperimentListResponse } from "@/lib/types";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ExperimentStatusBadge } from "@/components/experiments/ExperimentStatusBadge";
import Link from "next/link";

export default function HomePage() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [components, setComponents] = useState<ComponentState[]>([]);
  const [recentExperiments, setRecentExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    async function fetchData() {
      try {
        const [healthData, compData, expData] = await Promise.all([
          api.get<HealthStatus>("/api/health/status"),
          api.get<{ components: ComponentState[] }>("/api/components"),
          api.get<ExperimentListResponse>("/api/experiments?page=1&page_size=5").catch(() => ({ experiments: [], total: 0, page: 1, page_size: 5 })),
        ]);
        setHealth(healthData);
        setComponents(compData.components);
        setRecentExperiments(expData.experiments);
      } catch {
        // Error handled by api client
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <SystemHealth health={health} />
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-2">Quick Stats</h2>
              <div className="text-sm text-gray-500">
                <p>Components enabled: {components.filter(c => c.enabled).length} / {components.length}</p>
              </div>
            </div>
          </div>

          <ComponentInventory components={components} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-bioaf-400">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Recent Experiments</h3>
                <Link href="/experiments/new" className="text-sm text-bioaf-600 hover:text-bioaf-700">
                  + New Experiment
                </Link>
              </div>
              {recentExperiments.length === 0 ? (
                <p className="text-sm text-gray-400">No experiments yet</p>
              ) : (
                <div className="space-y-3">
                  {recentExperiments.map((exp) => (
                    <Link
                      key={exp.id}
                      href={`/experiments/${exp.id}`}
                      className="flex items-center justify-between hover:bg-gray-50 p-2 rounded -mx-2"
                    >
                      <div>
                        <p className="text-sm font-medium">{exp.name}</p>
                        <p className="text-xs text-gray-500">{exp.sample_count} samples</p>
                      </div>
                      <ExperimentStatusBadge status={exp.status} />
                    </Link>
                  ))}
                </div>
              )}
              {recentExperiments.length > 0 && (
                <Link href="/experiments" className="block text-sm text-bioaf-600 hover:text-bioaf-700 mt-4">
                  View all experiments →
                </Link>
              )}
            </div>
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-gray-300">
              <h3 className="font-semibold text-gray-400">Cost Summary</h3>
              <p className="text-sm text-gray-400 mt-2">Coming in Phase 7</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
