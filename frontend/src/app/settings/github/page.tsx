"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { api } from "@/lib/api";

interface GitHubStatus {
  connected: boolean;
  app_id: string | null;
  org_name: string | null;
  installation_id: string | null;
}

export default function SettingsGitHubPage() {
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Connect form fields
  const [appId, setAppId] = useState("");
  const [installationId, setInstallationId] = useState("");
  const [orgName, setOrgName] = useState("");
  const [privateKey, setPrivateKey] = useState("");

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await api.get<GitHubStatus>("/api/v1/settings/github/status");
      setStatus(data);
    } catch {
      setError("Failed to load GitHub status");
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    if (!appId || !installationId || !orgName || !privateKey) {
      setError("All fields are required");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.post("/api/v1/settings/github/connect", {
        app_id: appId,
        installation_id: installationId,
        org_name: orgName,
        private_key: privateKey,
      });
      setMessage("GitHub App connected");
      setAppId("");
      setInstallationId("");
      setOrgName("");
      setPrivateKey("");
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect");
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Disconnect the GitHub App? Notebook git integration will stop working.")) return;
    setError("");
    setMessage("");
    try {
      await api.delete("/api/v1/settings/github/disconnect");
      setMessage("GitHub App disconnected");
      await loadStatus();
    } catch {
      setError("Failed to disconnect");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setPrivateKey(reader.result as string);
    };
    reader.readAsText(file);
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">GitHub Integration</h1>

          {message && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">{message}</div>
          )}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
          )}

          {loading ? (
            <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>
          ) : status?.connected ? (
            /* Connected state */
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="text-sm font-medium text-green-700">Connected</span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="text-xs text-gray-500 block">Organization</label>
                  <p className="text-sm font-medium">{status.org_name}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block">App ID</label>
                  <p className="text-sm font-mono">{status.app_id}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 block">Installation ID</label>
                  <p className="text-sm font-mono">{status.installation_id}</p>
                </div>
              </div>

              <p className="text-xs text-gray-500 mb-4">
                Notebook sessions will automatically create git repositories and track changes for experiments with linked notebooks.
              </p>

              <button
                onClick={handleDisconnect}
                className="text-sm text-red-600 hover:text-red-800 border border-red-300 px-4 py-2 rounded hover:bg-red-50"
              >
                Disconnect GitHub App
              </button>
            </div>
          ) : (
            /* Disconnected state -- show connect form */
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-3 w-3 rounded-full bg-gray-300" />
                <span className="text-sm font-medium text-gray-500">Not Connected</span>
              </div>

              <p className="text-sm text-gray-600 mb-6">
                Connect a GitHub App to enable git-backed notebook history. The app needs Repository Contents (read/write) and Administration (read/write) permissions on your GitHub organization.
              </p>

              <div className="space-y-4 max-w-lg">
                <div>
                  <label className="text-sm text-gray-700 block mb-1">GitHub App ID</label>
                  <input
                    type="text"
                    value={appId}
                    onChange={(e) => setAppId(e.target.value)}
                    placeholder="123456"
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>

                <div>
                  <label className="text-sm text-gray-700 block mb-1">Installation ID</label>
                  <input
                    type="text"
                    value={installationId}
                    onChange={(e) => setInstallationId(e.target.value)}
                    placeholder="78901234"
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>

                <div>
                  <label className="text-sm text-gray-700 block mb-1">GitHub Organization</label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="my-biotech-org"
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>

                <div>
                  <label className="text-sm text-gray-700 block mb-1">Private Key (.pem file)</label>
                  <input
                    type="file"
                    accept=".pem"
                    onChange={handleFileUpload}
                    className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:bg-bioaf-50 file:text-bioaf-700 hover:file:bg-bioaf-100"
                  />
                  {privateKey && (
                    <p className="text-xs text-green-600 mt-1">Key loaded ({privateKey.length} characters)</p>
                  )}
                </div>

                <button
                  onClick={handleConnect}
                  disabled={saving || !appId || !installationId || !orgName || !privateKey}
                  className="bg-bioaf-600 text-white px-6 py-2 rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                >
                  {saving ? "Connecting..." : "Connect GitHub App"}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
