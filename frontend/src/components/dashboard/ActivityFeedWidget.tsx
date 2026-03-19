"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface ActivityEvent {
  id: number;
  event_type: string;
  summary: string;
  created_at: string;
  user_email?: string;
  severity?: string;
}

export function ActivityFeedWidget() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getWithRetry<{ events: ActivityEvent[] }>("/api/activity-feed?page_size=10")
      .then((data) => setEvents(data.events))
      .catch(() => setError("Failed to load activity feed"))
      .finally(() => setLoading(false));
  }, []);

  const severityColor: Record<string, string> = {
    info: "bg-blue-400",
    warning: "bg-amber-400",
    critical: "bg-red-400",
  };

  return (
    <div className="bg-white rounded-lg shadow p-5" data-testid="widget-activity-feed">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Recent Activity
        </h3>
        <Link
          href="/activity"
          className="text-xs text-bioaf-600 hover:text-bioaf-700 hover:underline"
          data-testid="activity-expand-button"
        >
          View all
        </Link>
      </div>
      {loading && (
        <div className="animate-pulse space-y-2" data-testid="widget-loading">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-6 bg-gray-100 rounded" />
          ))}
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
      {!loading && !error && events.length === 0 && (
        <p className="text-sm text-gray-400" data-testid="widget-empty">
          No recent activity. Events will appear here as you use the platform.
        </p>
      )}
      {!loading && !error && events.length > 0 && (
        <div className="space-y-2">
          {events.map((e) => (
            <div key={e.id} className="flex items-start gap-2">
              <span
                className={`w-1.5 h-1.5 mt-1.5 rounded-full flex-shrink-0 ${
                  severityColor[e.severity || "info"] || severityColor.info
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700 truncate">{e.summary}</p>
                <p className="text-xs text-gray-400">
                  {new Date(e.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
