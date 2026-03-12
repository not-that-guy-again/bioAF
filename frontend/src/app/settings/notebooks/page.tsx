"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";

interface NotebookConfig {
  idle_timeout_hours: number;
  idle_warning_minutes: number;
  max_sessions_per_user: number;
  bioaf_scrna_image: string;
}

export default function NotebookSettingsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<NotebookConfig>({
    idle_timeout_hours: 4,
    idle_warning_minutes: 15,
    max_sessions_per_user: 2,
    bioaf_scrna_image: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadConfig();
  }, [router]);

  async function loadConfig() {
    try {
      const data = await api.get<NotebookConfig>("/api/v1/settings/notebooks");
      setConfig(data);
    } catch {}
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.put("/api/v1/settings/notebooks", {
        idle_timeout_hours: config.idle_timeout_hours,
        idle_warning_minutes: config.idle_warning_minutes,
        max_sessions_per_user: config.max_sessions_per_user,
      });
      if (config.bioaf_scrna_image) {
        await api.put("/api/v1/settings/container-registry", {
          bioaf_scrna_image: config.bioaf_scrna_image,
        });
      }
      alert("Settings saved");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Notebook Settings</h1>

          <div className="bg-white rounded-lg shadow p-6 max-w-2xl space-y-6">
            <div>
              <label htmlFor="idle-timeout" className="block text-sm font-medium text-gray-700 mb-1">
                Idle Timeout (hours)
              </label>
              <input
                id="idle-timeout"
                type="number"
                min={1}
                max={12}
                value={config.idle_timeout_hours}
                onChange={(e) => setConfig({ ...config, idle_timeout_hours: Number(e.target.value) })}
                className="border rounded px-3 py-2 text-sm w-32"
              />
              <p className="text-xs text-gray-500 mt-1">
                Sessions idle longer than this will be auto-terminated (1-12 hours)
              </p>
            </div>

            <div>
              <label htmlFor="warning-minutes" className="block text-sm font-medium text-gray-700 mb-1">
                Warning Before Shutdown (minutes)
              </label>
              <input
                id="warning-minutes"
                type="number"
                min={5}
                max={60}
                value={config.idle_warning_minutes}
                onChange={(e) => setConfig({ ...config, idle_warning_minutes: Number(e.target.value) })}
                className="border rounded px-3 py-2 text-sm w-32"
              />
            </div>

            <div>
              <label htmlFor="max-sessions" className="block text-sm font-medium text-gray-700 mb-1">
                Max Sessions Per User
              </label>
              <input
                id="max-sessions"
                type="number"
                min={1}
                max={5}
                value={config.max_sessions_per_user}
                onChange={(e) => setConfig({ ...config, max_sessions_per_user: Number(e.target.value) })}
                className="border rounded px-3 py-2 text-sm w-32"
              />
            </div>

            <div>
              <label htmlFor="container-image" className="block text-sm font-medium text-gray-700 mb-1">
                Container Image URI
              </label>
              <input
                id="container-image"
                type="text"
                value={config.bioaf_scrna_image}
                onChange={(e) => setConfig({ ...config, bioaf_scrna_image: e.target.value })}
                className="border rounded px-3 py-2 text-sm w-full"
                placeholder="us-central1-docker.pkg.dev/project/repo/bioaf-scrna:latest"
              />
              <p className="text-xs text-gray-500 mt-1">
                Full Artifact Registry URI for the bioaf-scrna Docker image
              </p>
            </div>

            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-bioaf-600 text-white px-6 py-2 rounded-md text-sm hover:bg-bioaf-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}
