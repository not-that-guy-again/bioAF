"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { InfraComputeStatus, InfraComputeMetrics } from "@/lib/types";

export default function InfraComputePage() {
  const router = useRouter();
  const [status, setStatus] = useState<InfraComputeStatus | null>(null);
  const [metrics, setMetrics] = useState<InfraComputeMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [router]);

  async function loadData() {
    try {
      const [statusData, metricsData] = await Promise.all([
        api.get<InfraComputeStatus>("/api/v1/infrastructure/compute/status"),
        api.get<InfraComputeMetrics>("/api/v1/infrastructure/compute/metrics"),
      ]);
      setStatus(statusData);
      setMetrics(metricsData);
      setError(null);
    } catch {
      setError("Compute cluster is not enabled or unavailable");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">Compute Cluster</h1>
            <div className="flex gap-2">
              <Link href="/compute/jobs" className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm hover:bg-gray-50">
                Job Browser
              </Link>
              <Link href="/notebooks" className="bg-bioaf-600 text-white px-4 py-2 rounded-md text-sm hover:bg-bioaf-700">
                Notebooks
              </Link>
              <Link href="/compute/quotas" className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm hover:bg-gray-50">
                Quotas
              </Link>
            </div>
          </div>

          {loading && (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          )}

          {error && !loading && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
              <h2 className="text-lg font-semibold text-yellow-800 mb-2">Compute Cluster Not Available</h2>
              <p className="text-yellow-700 mb-4">{error}</p>
              <Link href="/infrastructure/components" className="text-bioaf-600 hover:text-bioaf-700 underline">
                Configure compute in the Component Catalog
              </Link>
            </div>
          )}

          {status && !loading && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Controller</p>
                  <p className="text-2xl font-bold mt-1">
                    <span className={status.controller_status === "running" ? "text-green-600" : "text-red-600"}>
                      {status.controller_status}
                    </span>
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Active Nodes</p>
                  <p className="text-2xl font-bold mt-1">
                    {status.active_nodes} <span className="text-base text-gray-400">/ {status.total_nodes}</span>
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Queue Depth</p>
                  <p className="text-2xl font-bold mt-1">{status.queue_depth}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">CPU / Memory</p>
                  <p className="text-2xl font-bold mt-1">
                    {metrics ? `${metrics.cpu_utilization_pct.toFixed(0)}%` : "—"}
                    <span className="text-base text-gray-400">
                      {metrics ? ` / ${metrics.memory_utilization_pct.toFixed(0)}%` : ""}
                    </span>
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Cost/Hour</p>
                  <p className="text-2xl font-bold mt-1">
                    {metrics ? `$${metrics.cost_burn_rate_hourly.toFixed(2)}` : "—"}
                  </p>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b">
                  <h2 className="text-lg font-semibold">Node Pools</h2>
                </div>
                <div className="divide-y">
                  {status.node_pools.length === 0 && (
                    <div className="p-6 text-center text-gray-400">No node pools found</div>
                  )}
                  {status.node_pools.map((pool) => {
                    const poolMetrics = metrics?.node_pools.find((m) => m.name === pool.name);
                    return (
                      <div key={pool.name} className="p-6 flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{pool.name}</h3>
                          <p className="text-sm text-gray-500">{pool.machine_type}</p>
                        </div>
                        <div className="flex gap-8 text-sm">
                          <div>
                            <span className="text-gray-500">Nodes:</span>{" "}
                            <span className="font-medium">{pool.current_nodes}</span>
                            <span className="text-gray-400"> ({pool.min_nodes}-{pool.max_nodes})</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Status:</span>{" "}
                            <span className={`font-medium ${pool.status === "healthy" ? "text-green-600" : "text-yellow-600"}`}>
                              {pool.status}
                            </span>
                          </div>
                          {poolMetrics && (
                            <div>
                              <span className="text-gray-500">CPU:</span>{" "}
                              <span className="font-medium">{poolMetrics.cpu_utilization_pct.toFixed(0)}%</span>
                              <span className="text-gray-400 mx-1">|</span>
                              <span className="text-gray-500">Mem:</span>{" "}
                              <span className="font-medium">{poolMetrics.memory_utilization_pct.toFixed(0)}%</span>
                            </div>
                          )}
                          {poolMetrics && poolMetrics.cost_rate_hourly > 0 && (
                            <div>
                              <span className="text-gray-500">$/hr:</span>{" "}
                              <span className="font-medium">${poolMetrics.cost_rate_hourly.toFixed(2)}</span>
                            </div>
                          )}
                          {pool.spot && (
                            <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Spot</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <p className="text-xs text-gray-400 text-center">Auto-refreshes every 30 seconds</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
