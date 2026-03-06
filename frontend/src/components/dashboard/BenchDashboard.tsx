"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ActivityFeedWidget } from "./ActivityFeedWidget";

interface Experiment {
  id: number;
  name: string;
  status: string;
}

export function BenchDashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.get<{ experiments: Experiment[] }>(
          "/api/experiments?page_size=5"
        );
        setExperiments(data.experiments);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">My Experiments</p>
          <p className="text-2xl font-bold text-gray-900">{experiments.length}</p>
          <Link href="/experiments" className="text-xs text-bioaf-600">View all</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Quick Actions</p>
          <div className="mt-2 space-y-1">
            <Link href="/experiments" className="block text-xs text-bioaf-600">Register Experiment</Link>
            <Link href="/data" className="block text-xs text-bioaf-600">Upload Data</Link>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Recent Experiments</p>
          {experiments.length === 0 ? (
            <p className="text-xs text-gray-400 mt-2">No experiments yet</p>
          ) : (
            <div className="mt-2 space-y-1">
              {experiments.slice(0, 3).map((e) => (
                <div key={e.id} className="text-xs">
                  <span className="text-gray-700">{e.name}</span>
                  <span className="ml-2 text-gray-400">{e.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <ActivityFeedWidget />
    </div>
  );
}
