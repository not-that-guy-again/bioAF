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

function StepBadge({ num, active }: { num: number; active: boolean }) {
  return (
    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${active ? "bg-bioaf-600 text-white" : "bg-gray-200 text-gray-500"}`}>
      {num}
    </span>
  );
}

export default function SettingsGitHubPage() {
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [orgName, setOrgName] = useState("");
  const [step, setStep] = useState(1);
  const [appSlug, setAppSlug] = useState("");

  const [appId, setAppId] = useState("");
  const [installationId, setInstallationId] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [saving, setSaving] = useState(false);

  const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
  const [appNameSuffix] = useState(() => Math.random().toString(36).slice(2, 6));

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
      setAppSlug("");
      await loadStatus();
    } catch {
      setError("Failed to disconnect");
    }
  };

  const appName = `bioAF-${orgName}-${appNameSuffix}`;

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
                  <p className="text-sm font-mono">{status.installation_id || "Not installed"}</p>
                </div>
              </div>
              <p className="text-xs text-gray-500 mb-4">
                Notebook sessions will automatically create git repositories and track changes for experiments with linked notebooks.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={async () => {
                    setError("");
                    setMessage("");
                    try {
                      const result = await api.post<{ status: string; message: string; repos?: string[] }>(
                        "/api/v1/settings/github/test"
                      );
                      if (result.status === "ok") {
                        setMessage(result.message + (result.repos?.length ? ` Repos: ${result.repos.join(", ")}` : ""));
                      } else {
                        setError(result.message);
                      }
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Test failed");
                    }
                  }}
                  className="text-sm border border-bioaf-600 text-bioaf-600 px-4 py-2 rounded hover:bg-bioaf-50"
                >
                  Test Connection
                </button>
                <button
                  onClick={handleDisconnect}
                  className="text-sm text-red-600 hover:text-red-800 border border-red-300 px-4 py-2 rounded hover:bg-red-50"
                >
                  Disconnect
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Step 1: Org name */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center gap-3 mb-4">
                  <StepBadge num={1} active={step >= 1} />
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
                  {step > 1 && (
                    <button onClick={() => { setStep(1); setAppSlug(""); }} className="mt-2 text-xs text-gray-400 hover:text-gray-600">Change</button>
                  )}
                </div>
              </div>

              {/* Step 2: Create the app */}
              {step >= 2 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <StepBadge num={2} active={step >= 2} />
                    <h2 className="text-base font-semibold">Create GitHub App</h2>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">
                    Open the link below. It will take you to GitHub where you can create a new app for your organization.
                    Fill in the fields using the exact values shown here.
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

                  <h3 className="text-sm font-medium mb-2">Copy these values into the GitHub form:</h3>
                  <div className="space-y-3 mb-5">
                    <CopyField label="GitHub App name" value={appName} />
                    <CopyField label="Homepage URL" value={baseUrl} mono />
                  </div>

                  <div className="space-y-3 mb-5">
                    <div className="bg-amber-50 border border-amber-200 rounded px-3 py-2">
                      <span className="text-xs text-amber-700 block">Webhook section</span>
                      <span className="text-sm text-amber-800">Uncheck the &ldquo;Active&rdquo; checkbox</span>
                    </div>
                  </div>

                  <h3 className="text-sm font-medium mb-2">Set these permissions:</h3>
                  <div className="space-y-1 text-sm bg-gray-50 rounded p-3 mb-5">
                    <p><strong>Repository permissions:</strong></p>
                    <p className="ml-4">Contents: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read and write</span></p>
                    <p className="ml-4">Administration: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read and write</span></p>
                    <p className="mt-2"><strong>Organization permissions:</strong></p>
                    <p className="ml-4">Members: <span className="font-mono bg-white px-1.5 py-0.5 rounded border text-xs">Read-only</span></p>
                  </div>

                  <h3 className="text-sm font-medium mb-2">At the bottom of the page:</h3>
                  <div className="text-sm bg-gray-50 rounded p-3 mb-5">
                    <p>Under &ldquo;Where can this GitHub App be installed?&rdquo;, select <strong>&ldquo;Only on this account&rdquo;</strong></p>
                  </div>

                  <p className="text-sm text-gray-600 mb-3">
                    Click <strong>&ldquo;Create GitHub App&rdquo;</strong> at the bottom.
                    After creation, you will see the <strong>App ID</strong> at the top of the app settings page.
                  </p>
                  <p className="text-sm text-gray-600 mb-3">
                    On the same page, scroll down to <strong>&ldquo;Private keys&rdquo;</strong> and click
                    {" "}<strong>&ldquo;Generate a private key&rdquo;</strong>. A <code>.pem</code> file will download automatically. Keep this file safe.
                  </p>

                  {step === 2 && (
                    <div className="mt-4">
                      <label className="text-sm text-gray-700 block mb-1">
                        Enter the app name you used (so we can build the install link):
                      </label>
                      <div className="flex gap-2 max-w-md">
                        <input
                          type="text"
                          value={appSlug}
                          onChange={(e) => setAppSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
                          placeholder={appName.toLowerCase()}
                          className="flex-1 px-3 py-2 border rounded text-sm font-mono"
                        />
                        <button
                          onClick={() => setStep(3)}
                          disabled={!appSlug.trim()}
                          className="bg-bioaf-600 text-white px-4 py-2 rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                        >
                          Continue
                        </button>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        This is the app name converted to lowercase with hyphens (shown in the URL on the app settings page)
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: Install the app */}
              {step >= 3 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <StepBadge num={3} active={step >= 3} />
                    <h2 className="text-base font-semibold">Install App on Organization</h2>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">
                    Now install the app on your <strong>{orgName}</strong> organization. Click the link below, then
                    click <strong>&ldquo;Install&rdquo;</strong> on the GitHub page.
                  </p>

                  <a
                    href={`https://github.com/apps/${appSlug}/installations/new`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded text-sm hover:bg-gray-800 mb-5"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    Install App on {orgName}
                  </a>

                  <p className="text-sm text-gray-600 mb-3">
                    After clicking Install, look at the URL in your browser. It will look like:
                  </p>
                  <div className="bg-gray-50 rounded px-3 py-2 mb-3 font-mono text-sm">
                    github.com/organizations/{orgName}/settings/installations/<strong className="text-bioaf-600">12345678</strong>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">
                    The number at the end is your <strong>Installation ID</strong>. You will need it in the next step.
                  </p>

                  {step === 3 && (
                    <button
                      onClick={() => setStep(4)}
                      className="bg-bioaf-600 text-white px-4 py-2 rounded text-sm hover:bg-bioaf-700"
                    >
                      Continue
                    </button>
                  )}
                </div>
              )}

              {/* Step 4: Enter credentials */}
              {step >= 4 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <StepBadge num={4} active={step >= 4} />
                    <h2 className="text-base font-semibold">Connect</h2>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">
                    Enter the App ID and Installation ID from the previous steps, and upload the private key file (.pem) you downloaded.
                  </p>

                  <div className="max-w-md space-y-4">
                    <div>
                      <label className="text-sm text-gray-700 block mb-1">App ID</label>
                      <input
                        type="text"
                        value={appId}
                        onChange={(e) => setAppId(e.target.value)}
                        placeholder="3206995"
                        className="w-full px-3 py-2 border rounded text-sm font-mono"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        Shown at the top of your app&apos;s settings page after creation (step 2)
                      </p>
                    </div>

                    <div>
                      <label className="text-sm text-gray-700 block mb-1">Installation ID</label>
                      <input
                        type="text"
                        value={installationId}
                        onChange={(e) => setInstallationId(e.target.value)}
                        placeholder="12345678"
                        className="w-full px-3 py-2 border rounded text-sm font-mono"
                      />
                      <p className="text-xs text-gray-400 mt-1">
                        The number from the URL after installing the app on your org (step 3)
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
                      <p className="text-xs text-gray-400 mt-1">
                        Downloaded from your app&apos;s settings page under &ldquo;Private keys&rdquo; (step 2)
                      </p>
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
                        onClick={() => setStep(3)}
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
