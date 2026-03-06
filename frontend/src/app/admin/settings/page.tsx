"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated, getCurrentUser } from "@/lib/auth";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    const user = getCurrentUser();
    if (user?.role !== "admin") { router.push("/"); return; }
  }, [router]);

  const handleSaveSmtp = async () => {
    setError("");
    setMessage("");
    try {
      await api.post("/api/bootstrap/configure-smtp", {
        host: smtpHost,
        port: parseInt(smtpPort),
        username: smtpUsername,
        password: smtpPassword,
        from_address: smtpFrom,
      });
      setMessage("SMTP configuration saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save SMTP settings");
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Admin Settings</h1>

          {/* SMTP Configuration */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">SMTP Configuration</h2>

            {message && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">{message}</div>}
            {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
                <input type="text" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} className="w-full px-3 py-2 border rounded" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                <input type="number" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} className="w-full px-3 py-2 border rounded" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input type="text" value={smtpUsername} onChange={(e) => setSmtpUsername(e.target.value)} className="w-full px-3 py-2 border rounded" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} className="w-full px-3 py-2 border rounded" />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">From Address</label>
                <input type="email" value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} className="w-full px-3 py-2 border rounded" />
              </div>
            </div>
            <button onClick={handleSaveSmtp} className="mt-4 px-4 py-2 bg-bioaf-600 text-white rounded hover:bg-bioaf-700">
              Save SMTP Settings
            </button>
          </div>

          {/* Slack Webhook Placeholder */}
          <div className="bg-white rounded-lg shadow p-6 mb-6 border-l-4 border-gray-300">
            <h2 className="text-lg font-semibold text-gray-400">Slack Webhook</h2>
            <p className="text-sm text-gray-400 mt-2">Full notification system coming in Phase 7</p>
          </div>

          {/* Version Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-2">Platform Info</h2>
            <p className="text-sm text-gray-600">bioAF Version: <strong>0.1.0</strong></p>
          </div>
        </main>
      </div>
    </div>
  );
}
