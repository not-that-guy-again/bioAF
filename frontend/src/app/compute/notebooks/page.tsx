"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type {
  NotebookSession,
  SessionListResponse,
  SessionLaunchRequest,
  ResourceProfile,
  SessionType,
  Experiment,
  ExperimentListResponse,
} from "@/lib/types";
import { RESOURCE_PROFILES } from "@/lib/types";

const SESSION_STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  starting: "bg-blue-100 text-blue-800",
  running: "bg-green-100 text-green-800",
  idle: "bg-yellow-100 text-yellow-800",
  stopping: "bg-orange-100 text-orange-800",
  stopped: "bg-gray-100 text-gray-600",
  failed: "bg-red-100 text-red-800",
};

export default function NotebookSessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<NotebookSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<ResourceProfile>("small");
  const [selectedExperiment, setSelectedExperiment] = useState<number | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadSessions();
    loadExperiments();
  }, [router]);

  async function loadSessions() {
    try {
      const data = await api.get<SessionListResponse>("/api/notebooks/sessions");
      setSessions(data.sessions);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function loadExperiments() {
    try {
      const data = await api.get<ExperimentListResponse>("/api/experiments?page_size=100");
      setExperiments(data.experiments);
    } catch {}
  }

  async function handleLaunch(sessionType: SessionType) {
    setLaunching(true);
    try {
      const req: SessionLaunchRequest = {
        session_type: sessionType,
        resource_profile: selectedProfile,
        experiment_id: selectedExperiment,
      };
      await api.post("/api/notebooks/sessions", req);
      loadSessions();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to launch session");
    } finally {
      setLaunching(false);
    }
  }

  async function handleStop(sessionId: number) {
    try {
      await api.post(`/api/notebooks/sessions/${sessionId}/stop`);
      loadSessions();
    } catch {}
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-4 mb-6">
            <Link href="/compute" className="text-gray-500 hover:text-gray-700">← Cluster</Link>
            <h1 className="text-2xl font-bold">Notebook Sessions</h1>
          </div>

          {/* Launch Section */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Launch New Session</h2>

            <div className="flex flex-col gap-4">
              {/* Resource Profile Selector */}
              <div>
                <label className="text-sm text-gray-500 mb-2 block">Resource Profile</label>
                <div className="flex gap-3">
                  {(["small", "medium", "large"] as ResourceProfile[]).map((profile) => {
                    const specs = RESOURCE_PROFILES[profile];
                    return (
                      <button
                        key={profile}
                        onClick={() => setSelectedProfile(profile)}
                        className={`border rounded-lg px-4 py-3 text-sm ${
                          selectedProfile === profile
                            ? "border-bioaf-500 bg-bioaf-50 text-bioaf-700"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                      >
                        <div className="font-semibold capitalize">{profile}</div>
                        <div className="text-xs text-gray-500">{specs.cpu} CPU, {specs.memory}GB RAM</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Optional Experiment Link */}
              <div>
                <label className="text-sm text-gray-500 mb-2 block">Link to Experiment (optional)</label>
                <select
                  value={selectedExperiment || ""}
                  onChange={(e) => setSelectedExperiment(e.target.value ? Number(e.target.value) : null)}
                  className="border rounded px-3 py-2 text-sm w-64"
                >
                  <option value="">No experiment</option>
                  {experiments.map((exp) => (
                    <option key={exp.id} value={exp.id}>{exp.name}</option>
                  ))}
                </select>
              </div>

              {/* Launch Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => handleLaunch("jupyter")}
                  disabled={launching}
                  className="bg-bioaf-600 text-white px-6 py-2 rounded-md text-sm hover:bg-bioaf-700 disabled:opacity-50"
                >
                  {launching ? "Launching..." : "Launch Jupyter"}
                </button>
                <button
                  onClick={() => handleLaunch("rstudio")}
                  disabled={launching}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {launching ? "Launching..." : "Launch RStudio"}
                </button>
              </div>
            </div>
          </div>

          {/* Active Sessions */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold">Active Sessions</h2>
            </div>

            {loading ? (
              <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profile</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Start Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Idle</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Experiment</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {sessions.map((s) => (
                    <tr key={s.id} className={s.status === "idle" ? "bg-yellow-50" : "hover:bg-gray-50"}>
                      <td className="px-4 py-3 text-sm capitalize font-medium">{s.session_type}</td>
                      <td className="px-4 py-3 text-sm">{s.user?.name || s.user?.email || "—"}</td>
                      <td className="px-4 py-3 text-sm capitalize">
                        {s.resource_profile} ({s.cpu_cores} CPU, {s.memory_gb}GB)
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${SESSION_STATUS_COLORS[s.status] || "bg-gray-100"}`}>
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {s.started_at ? new Date(s.started_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {s.idle_since ? (
                          <span className="text-yellow-700">
                            Since {new Date(s.idle_since).toLocaleTimeString()}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {s.experiment ? (
                          <Link href={`/experiments/${s.experiment.id}`} className="text-bioaf-600 hover:underline">
                            {s.experiment.name}
                          </Link>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {s.proxy_url && s.status === "running" && (
                            <a
                              href={s.proxy_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-bioaf-600 hover:text-bioaf-800"
                            >
                              Open
                            </a>
                          )}
                          {["pending", "starting", "running", "idle"].includes(s.status) && (
                            <button
                              onClick={() => handleStop(s.id)}
                              className="text-xs text-red-600 hover:text-red-800"
                            >
                              Stop
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {sessions.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No active sessions</td></tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
