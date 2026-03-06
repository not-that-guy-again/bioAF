"use client";

import { StatusBadge } from "@/components/shared/StatusBadge";
import type { HealthStatus } from "@/lib/types";

interface SystemHealthProps {
  health: HealthStatus | null;
}

export function SystemHealth({ health }: SystemHealthProps) {
  if (!health) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">System Health</h2>
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">System Health</h2>
        <StatusBadge status={health.status} />
      </div>
      <div className="space-y-3">
        {Object.entries(health.services).map(([name, service]) => (
          <div key={name} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <span className="text-sm font-medium capitalize">{name}</span>
            <StatusBadge status={service.status} />
          </div>
        ))}
      </div>
    </div>
  );
}
