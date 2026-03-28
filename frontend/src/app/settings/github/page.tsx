"use client";

import { useEffect, useState, useCallback } from "react";
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

function CopyField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    try {
      // Try modern clipboard API first (requires HTTPS)
      navigator.clipboard.writeText(value).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }).catch(() => fallbackCopy());
    } catch {
      fallbackCopy();
    }
  };

  const fallbackCopy = () => {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center justify-between bg-gray-50 rounded px-3 py-2">
      <div>
        <span className="text-xs text-gray-500 block">{label}</span>
        <span className={`text-sm ${mono ? "font-mono" : ""} select-all`}>{value}</span>
      </div>
      <button
        onClick={handleCopy}
        className="text-xs px-2 py-1 border rounded text-gray-600 hover:bg-white ml-4 shrink-0"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

export default function SettingsGitHubPage() {
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Step 1: org name
  const [orgName, setOrgName] = useState("");
  const [step, setStep] = useState(1);

  // Step 3: credentials
  const [appId, setAppId] = useState("");
  const [installationId, setInstallationId] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [saving, setSaving] = useState(false);

  const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
  const [appNameSuffix] = useState(() => Math.random().toString(36).slice(2, 6));
  const callbackUrl = `${baseUrl}/api/v1/settings/github/callback`;

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
    loadStatus();
  }, [loadStatus]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setPrivateKey(reader.result as string);
    reader.readAsText(file);
  };

  const handleConnect = async () => {
    if (!appId || !installationId || !privateKey) {
      setError("All three fields are required");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.post("/api/v1/settings/github/connect", {
        app_id: appId,
        installation_id: installationId,
        org_name: orgName,
        private_key: privateKey,
      });
      setMessage("GitHub App connected successfully");
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
      setStep(1);
      setOrgName("");
      setAppId("");
      setInstallationId("");
      setPrivateKey("");
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
                Disconnect
              </button>
            </div>
          ) : (
            /* Setup wizard */
            <div className="space-y-6">
              {/* Step 1: Org name */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center gap-3 mb-4">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step >= 1 ? "bg-bioaf-600 text-white" : "bg-gray-200 text-gray-500"}`}>1</span>
                  <h2 className="text-base font-semibold">GitHub Organization</h2>
                </div>

                <div className="max-w-md">
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="my-biotech-org"
                    className="w-full px-3 py-2 border rounded text-sm"
                    disabled={step > 1}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Your GitHub organization name (from the URL: github.com/orgs/<strong>this-part</strong>)
                  </p>
                  {step === 1 && (
                    <button
                      onClick={() => orgName.trim() && setStep(2)}
                      disabled={!orgName.trim()}
                      className="mt-3 bg-bioaf-600 text-white px-4 py-2 rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                    >
                      Continue
                    </button>
                  )}
                </div>
              </div>

              {/* Step 2: Create app on GitHub */}
              {step >= 2 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step >= 2 ? "bg-bioaf-600 text-white" : "bg-gray-200 text-gray-500"}`}>2</span>
                    <h2 className="text-base font-semibold">Create GitHub App</h2>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">
                    Open the link below and fill in the fields using the values provided. Copy each value exactly.
                  </p>

                  <a
                    href={`https://github.com/organizations/${orgName}/settings/apps/new`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded text-sm hover:bg-gray-800 mb-5"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    Open GitHub App Creation Page
                  </a>

                  <div className="space-y-3 mb-5">
                    <CopyField label="GitHub App name" value={`bioAF-${orgName}-${appNameSuffix}`} />
                    <CopyField label="Homepage URL" value={baseUrl} mono />
                    <div className="bg-amber-50 border border-amber-200 rounded px-3 py-2">
                      <span className="text-xs text-amber-700 block">Webhook</span>
                      <span className="text-sm text-amber-800">Uncheck &ldquo;Active&rdquo; (webhooks are not needed)</span>
                    </div>
                  </div>

                  <div className="mb-5">
                    <h3 className="text-sm font-medium mb-2">Permissions (expand each section and set these):</h3>
                    <div className="space-y-1 text-sm bg-gray-50 rounded p-3">
                      <p><strong>Repository permissions:</strong></p>
                      <p className="ml-4">Contents: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read and write</span></p>
                      <p className="ml-4">Administration: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read and write</span></p>
                      <p className="mt-2"><strong>Organization permissions:</strong></p>
                      <p className="ml-4">Members: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read-only</span></p>
                    </div>
                  </div>

                  <div className="mb-5">
                    <h3 className="text-sm font-medium mb-2">Installation scope:</h3>
                    <div className="text-sm bg-gray-50 rounded p-3">
                      <p>Select: <strong>&ldquo;Only on this account&rdquo;</strong></p>
                    </div>
                  </div>

                  <p className="text-sm text-gray-600 mb-3">
                    After clicking <strong>&ldquo;Create GitHub App&rdquo;</strong>, GitHub will show you the App ID and prompt you to generate a private key.
                    Download the private key file (.pem) -- you will upload it in the next step.
                  </p>
                  <p className="text-sm text-gray-600 mb-4">
                    Then click <strong>&ldquo;Install App&rdquo;</strong> in the left sidebar and install it on your <strong>{orgName}</strong> organization.
                    The installation ID will appear in the URL after installation (the number at the end).
                  </p>

                  {step === 2 && (
                    <button
                      onClick={() => setStep(3)}
                      className="bg-bioaf-600 text-white px-4 py-2 rounded text-sm hover:bg-bioaf-700"
                    >
                      I have created and installed the app
                    </button>
                  )}
                </div>
              )}

              {/* Step 3: Enter credentials */}
              {step >= 3 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold bg-bioaf-600 text-white">3</span>
                    <h2 className="text-base font-semibold">Connect</h2>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">
                    Enter the App ID and Installation ID from GitHub, and upload the private key (.pem) file you downloaded.
                  </p>

                  <div className="max-w-md space-y-4">
                    <div>
                      <label className="text-sm text-gray-700 block mb-1">App ID</label>
                      <input
                        type="text"
                        value={appId}
                        onChange={(e) => setAppId(e.target.value)}
                        placeholder="123456"
                        className="w-full px-3 py-2 border rounded text-sm font-mono"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Found at the top of your app&apos;s settings page on GitHub
                      </p>
                    </div>

                    <div>
                      <label className="text-sm text-gray-700 block mb-1">Installation ID</label>
                      <input
                        type="text"
                        value={installationId}
                        onChange={(e) => setInstallationId(e.target.value)}
                        placeholder="78901234"
                        className="w-full px-3 py-2 border rounded text-sm font-mono"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        The number at the end of the URL after installing the app (github.com/...installations/<strong>this-number</strong>)
                      </p>
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

                    <div className="flex gap-3">
                      <button
                        onClick={handleConnect}
                        disabled={saving || !appId || !installationId || !privateKey}
                        className="bg-bioaf-600 text-white px-6 py-2 rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                      >
                        {saving ? "Connecting..." : "Connect"}
                      </button>
                      <button
                        onClick={() => setStep(2)}
                        className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2"
                      >
                        Back
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
