"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ClusterStatus } from "@/lib/types";

export default function ComputePage() {
  const router = useRouter();
  const [cluster, setCluster] = useState<ClusterStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadClusterStatus();
    const interval = setInterval(loadClusterStatus, 30000);
    return () => clearInterval(interval);
  }, [router]);

  async function loadClusterStatus() {
    try {
      const data = await api.get<ClusterStatus>("/api/compute/cluster");
      setCluster(data);
      setError(null);
    } catch (err) {
      setError("SLURM cluster is not enabled or unavailable");
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
            <h1 className="text-2xl font-bold">Cluster Status</h1>
            <div className="flex gap-2">
              <Link href="/compute/jobs" className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm hover:bg-gray-50">
                Job Browser
              </Link>
              <Link href="/compute/notebooks" className="bg-bioaf-600 text-white px-4 py-2 rounded-md text-sm hover:bg-bioaf-700">
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
              <h2 className="text-lg font-semibold text-yellow-800 mb-2">SLURM Cluster Not Available</h2>
              <p className="text-yellow-700 mb-4">{error}</p>
              <Link href="/components" className="text-bioaf-600 hover:text-bioaf-700 underline">
                Enable SLURM in the Component Catalog
              </Link>
            </div>
          )}

          {cluster && !loading && (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Controller</p>
                  <p className="text-2xl font-bold mt-1">
                    <span className={cluster.controller_status === "running" ? "text-green-600" : "text-red-600"}>
                      {cluster.controller_status}
                    </span>
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Total Nodes</p>
                  <p className="text-2xl font-bold mt-1">
                    {cluster.active_nodes} <span className="text-base text-gray-400">/ {cluster.total_nodes}</span>
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Queue Depth</p>
                  <p className="text-2xl font-bold mt-1">{cluster.queue_depth}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <p className="text-sm text-gray-500">Estimated Cost/Hour</p>
                  <p className="text-2xl font-bold mt-1">
                    {cluster.cost_burn_rate_hourly != null
                      ? `$${cluster.cost_burn_rate_hourly.toFixed(2)}`
                      : "—"}
                  </p>
                </div>
              </div>

              {/* Partition Details */}
              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b">
                  <h2 className="text-lg font-semibold">Partitions</h2>
                </div>
                <div className="divide-y">
                  {cluster.partitions.length === 0 && (
                    <div className="p-6 text-center text-gray-400">No partitions found</div>
                  )}
                  {cluster.partitions.map((p) => (
                    <div key={p.name} className="p-6 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold capitalize">{p.name}</h3>
                        <p className="text-sm text-gray-500">{p.instance_type}</p>
                      </div>
                      <div className="flex gap-8 text-sm">
                        <div>
                          <span className="text-gray-500">Active:</span>{" "}
                          <span className="font-medium">{p.active_nodes}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Idle:</span>{" "}
                          <span className="font-medium">{p.idle_nodes}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Max:</span>{" "}
                          <span className="font-medium">{p.max_nodes}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Queue:</span>{" "}
                          <span className="font-medium">{p.queue_depth}</span>
                        </div>
                        {p.use_spot && (
                          <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Spot</span>
                        )}
                      </div>
                    </div>
                  ))}
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
