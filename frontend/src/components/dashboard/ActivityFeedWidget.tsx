"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface ActivityEvent {
  id: number;
  event_type: string;
  summary: string;
  created_at: string;
}

export function ActivityFeedWidget() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.get<{ events: ActivityEvent[] }>(
          "/api/activity-feed?page_size=10"
        );
        setEvents(data.events);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Recent Activity</h3>
        <Link href="/activity" className="text-xs text-bioaf-600 hover:text-bioaf-700">
          View all
        </Link>
      </div>
      {events.length === 0 ? (
        <p className="text-sm text-gray-500">No recent activity</p>
      ) : (
        <div className="space-y-2">
          {events.map((e) => (
            <div key={e.id} className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 mt-1.5 rounded-full bg-bioaf-500 flex-shrink-0" />
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
