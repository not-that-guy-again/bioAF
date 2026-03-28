"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [orgName, setOrgName] = useState("");
  const [redirecting, setRedirecting] = useState(false);
  const callbackHandled = useRef(false);

  const loadStatus = useCallback(async () => {
    try {
      const data = await api.get<GitHubStatus>("/api/v1/settings/github/status");
      setStatus(data);
    } catch {
      setError("Failed to load GitHub status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Check for GitHub callback code in URL
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code && !callbackHandled.current) {
      callbackHandled.current = true;
      setLoading(true);
      setError("");
      api.post("/api/v1/settings/github/callback", { code })
        .then(() => {
          setMessage("GitHub App connected successfully");
          return loadStatus();
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Failed to complete GitHub setup");
          setLoading(false);
        })
        .finally(() => {
          window.history.replaceState({}, "", "/settings/github");
        });
    } else {
      loadStatus();
    }
  }, [loadStatus]);

  const handleInstall = async () => {
    if (!orgName.trim()) {
      setError("Enter your GitHub organization name");
      return;
    }
    setError("");
    setRedirecting(true);

    try {
      const callbackUrl = `${window.location.origin}/settings/github`;
      const data = await api.post<{ manifest: object; redirect_url: string }>(
        "/api/v1/settings/github/manifest",
        { org_name: orgName.trim(), callback_url: callbackUrl }
      );

      // Create a form and POST the manifest to GitHub
      const form = document.createElement("form");
      form.method = "POST";
      form.action = data.redirect_url;
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "manifest";
      input.value = JSON.stringify(data.manifest);
      form.appendChild(input);
      document.body.appendChild(form);
      form.submit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start GitHub setup");
      setRedirecting(false);
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
                Disconnect
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-3 w-3 rounded-full bg-gray-300" />
                <span className="text-sm font-medium text-gray-500">Not Connected</span>
              </div>

              <p className="text-sm text-gray-600 mb-6">
                Connect your GitHub organization to enable git-backed notebook history. Notebooks will automatically track
                changes in private repositories under your org.
              </p>

              <div className="max-w-md space-y-4">
                <div>
                  <label className="text-sm text-gray-700 block mb-1">GitHub Organization Name</label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="my-biotech-org"
                    className="w-full px-3 py-2 border rounded text-sm"
                    onKeyDown={(e) => e.key === "Enter" && handleInstall()}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    The name of your GitHub organization (not your personal account)
                  </p>
                </div>

                <button
                  onClick={handleInstall}
                  disabled={redirecting || !orgName.trim()}
                  className="flex items-center gap-2 bg-gray-900 text-white px-5 py-2.5 rounded text-sm hover:bg-gray-800 disabled:opacity-50"
                >
                  {redirecting ? (
                    <>
                      <LoadingSpinner size="sm" />
                      Redirecting to GitHub...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                      </svg>
                      Install on GitHub
                    </>
                  )}
                </button>

                <p className="text-xs text-gray-400">
                  You will be redirected to GitHub to approve the app installation. The app will have read/write access
                  to repository contents and administration within your organization.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
