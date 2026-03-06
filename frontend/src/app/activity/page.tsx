"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";

interface ActivityEvent {
  id: number;
  user_id: number | null;
  event_type: string;
  entity_type: string | null;
  entity_id: number | null;
  summary: string;
  created_at: string;
}

const eventTypeIcons: Record<string, string> = {
  "pipeline.completed": "check-circle",
  "pipeline.failed": "x-circle",
  "experiment.status_changed": "flask",
  "data.uploaded": "upload",
  "backup.failure": "shield",
  "budget.threshold_80": "dollar",
};

export default function ActivityFeedPage() {
  const router = useRouter();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [eventTypeFilter, setEventTypeFilter] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); }
  }, [router]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        let url = `/api/activity-feed?page=${page}&page_size=50`;
        if (eventTypeFilter) url += `&event_type=${eventTypeFilter}`;
        const data = await api.get<{ events: ActivityEvent[]; total: number }>(url);
        setEvents(data.events);
        setTotal(data.total);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [page, eventTypeFilter]);

  const totalPages = Math.ceil(total / 50);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Activity Feed</h1>

          <div className="mb-4">
            <select
              value={eventTypeFilter}
              onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1); }}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            >
              <option value="">All events</option>
              <option value="pipeline.completed">Pipeline Completed</option>
              <option value="pipeline.failed">Pipeline Failed</option>
              <option value="experiment.status_changed">Experiment Changed</option>
              <option value="data.uploaded">Data Uploaded</option>
              <option value="backup.failure">Backup Failure</option>
              <option value="budget.threshold_50">Budget 50%</option>
              <option value="budget.threshold_80">Budget 80%</option>
              <option value="budget.threshold_100">Budget 100%</option>
            </select>
          </div>

          <div className="bg-white rounded-lg border border-gray-200">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : events.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No activity yet</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {events.map((event) => (
                  <div key={event.id} className="px-4 py-3 hover:bg-gray-50">
                    <div className="flex items-start gap-3">
                      <div className="w-2 h-2 mt-2 rounded-full bg-bioaf-500 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{event.summary}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs font-mono text-gray-400">{event.event_type}</span>
                          {event.entity_type && (
                            <span className="text-xs text-gray-400">
                              {event.entity_type} #{event.entity_id}
                            </span>
                          )}
                          <span className="text-xs text-gray-400">
                            {new Date(event.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Previous</button>
              <span className="px-3 py-1 text-sm text-gray-600">Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Next</button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
