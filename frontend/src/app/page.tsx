"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { SystemHealth } from "@/components/dashboard/SystemHealth";
import { ComponentInventory } from "@/components/dashboard/ComponentInventory";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { HealthStatus, ComponentState } from "@/lib/types";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

export default function HomePage() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [components, setComponents] = useState<ComponentState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    async function fetchData() {
      try {
        const [healthData, compData] = await Promise.all([
          api.get<HealthStatus>("/api/health/status"),
          api.get<{ components: ComponentState[] }>("/api/components"),
        ]);
        setHealth(healthData);
        setComponents(compData.components);
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
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-gray-300">
              <h3 className="font-semibold text-gray-400">Experiment Summary</h3>
              <p className="text-sm text-gray-400 mt-2">Coming in Phase 2</p>
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
