"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { ContentLoading } from "@/components/shared/ContentLoading";

interface SessionCredentialResponse {
  configured: boolean;
  username: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export default function SessionCredentialsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [cred, setCred] = useState<SessionCredentialResponse | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadCredentials();
  }, [router]);

  const loadCredentials = async () => {
    try {
      const data = await api.get<SessionCredentialResponse>(
        "/api/auth/me/session-credentials",
      );
      setCred(data);
      if (data.username) setUsername(data.username);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setError("");
    setMessage("");

    if (!password) {
      setError("Password is required");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setSaving(true);
    try {
      const body: Record<string, string> = { password };
      if (username) body.username = username;

      const data = await api.put<SessionCredentialResponse>(
        "/api/auth/me/session-credentials",
        body,
      );
      setCred(data);
      setPassword("");
      setConfirmPassword("");
      setMessage(
        data.username
          ? `Session credentials saved. Your RStudio username is: ${data.username}`
          : "Session credentials saved",
      );
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Failed to save credentials",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Session Credentials
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            These credentials are used to log into RStudio sessions launched
            from bioAF. They are separate from your platform login.
          </p>

          {message && (
            <div className="mb-4 p-3 rounded bg-green-50 border border-green-200 text-green-700 text-sm">
              {message}
            </div>
          )}
          {error && (
            <div className="mb-4 p-3 rounded bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <ContentLoading />
          ) : (
            <div className="max-w-lg">
              {cred?.configured && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="text-sm font-semibold text-blue-800 mb-1">
                    Current credentials
                  </h3>
                  <p className="text-sm text-blue-700">
                    Username: <span className="font-mono font-bold">{cred.username}</span>
                  </p>
                  {cred.updated_at && (
                    <p className="text-xs text-blue-500 mt-1">
                      Last updated: {new Date(cred.updated_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}

              <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  {cred?.configured
                    ? "Update credentials"
                    : "Set up session credentials"}
                </h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Username (optional)
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Auto-generated from your email"
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bioaf-500"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Lowercase letters, numbers, and underscores. 3-32 characters.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={cred?.configured ? "Enter new password" : "Choose a password"}
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bioaf-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirm password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm your password"
                    className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bioaf-500"
                  />
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="w-full bg-bioaf-600 text-white px-4 py-2 rounded-md hover:bg-bioaf-700 disabled:opacity-50 text-sm font-medium"
                >
                  {saving
                    ? "Saving..."
                    : cred?.configured
                      ? "Update Credentials"
                      : "Set Up Credentials"}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
