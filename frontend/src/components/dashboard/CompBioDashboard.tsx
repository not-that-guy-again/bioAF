"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ActivityFeedWidget } from "./ActivityFeedWidget";

export function CompBioDashboard() {
  const [pipelineRuns, setPipelineRuns] = useState(0);
  const [notebooks, setNotebooks] = useState(0);

  useEffect(() => {
    const load = async () => {
      try {
        const [runs, nb] = await Promise.all([
          api.get<{ total: number }>("/api/pipeline-runs?page_size=1").catch(() => ({ total: 0 })),
          api.get<{ total: number }>("/api/notebooks?page_size=1").catch(() => ({ total: 0 })),
        ]);
        setPipelineRuns(runs.total);
        setNotebooks(nb.total);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Pipeline Runs</p>
          <p className="text-2xl font-bold text-gray-900">{pipelineRuns}</p>
          <Link href="/pipelines/runs" className="text-xs text-bioaf-600">View runs</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Notebook Sessions</p>
          <p className="text-2xl font-bold text-gray-900">{notebooks}</p>
          <Link href="/compute" className="text-xs text-bioaf-600">View compute</Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Quick Actions</p>
          <div className="mt-2 space-y-1">
            <Link href="/compute" className="block text-xs text-bioaf-600">Launch Notebook</Link>
            <Link href="/pipelines" className="block text-xs text-bioaf-600">Browse Pipelines</Link>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Resources</p>
          <div className="mt-2 space-y-1">
            <Link href="/packages" className="block text-xs text-bioaf-600">Packages</Link>
            <Link href="/environments" className="block text-xs text-bioaf-600">Environments</Link>
            <Link href="/results" className="block text-xs text-bioaf-600">Results</Link>
          </div>
        </div>
      </div>
      <ActivityFeedWidget />
    </div>
  );
}
