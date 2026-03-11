"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ComponentHealth {
  name: string;
  status: string;
  enabled: boolean;
}

export function InfrastructureHealthWidget() {
  const [components, setComponents] = useState<ComponentHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ components: ComponentHealth[] }>("/api/components")
      .then((data) => setComponents(data.components.filter((c) => c.enabled)))
      .catch(() => setError("Failed to load component health"))
      .finally(() => setLoading(false));
  }, []);

  const statusColor: Record<string, string> = {
    healthy: "bg-green-400",
    degraded: "bg-yellow-400",
    unhealthy: "bg-red-400",
    unknown: "bg-gray-400",
  };

  return (
    <div className="bg-white rounded-lg shadow p-5" data-testid="widget-infrastructure-health">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Infrastructure Health
      </h3>
      {loading && (
        <div className="animate-pulse space-y-2" data-testid="widget-loading">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-gray-100 rounded" />
          ))}
        </div>
      )}
      {error && (
        <div className="text-sm text-red-600" data-testid="widget-error">
          {error}
          <button
            onClick={() => window.location.reload()}
            className="ml-2 text-bioaf-600 hover:underline"
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && components.length === 0 && (
        <p className="text-sm text-gray-400" data-testid="widget-empty">
          No enabled components found. Enable components in Infrastructure settings.
        </p>
      )}
      {!loading && !error && components.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {components.map((c) => (
            <div key={c.name} className="flex items-center gap-2 px-2 py-1.5 rounded bg-gray-50">
              <span className={`w-2 h-2 rounded-full ${statusColor[c.status] || statusColor.unknown}`} />
              <span className="text-sm text-gray-700 truncate">{c.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
