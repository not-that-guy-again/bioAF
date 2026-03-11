"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";

export default function SettingsSmtpPage() {
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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

  const handleTestEmail = async () => {
    try {
      await api.post("/api/notifications/test", { channel: "email" });
      setMessage("Test email sent successfully");
    } catch {
      setError("Failed to send test email");
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">SMTP Configuration</h1>

          {message && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">{message}</div>}
          {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}

          <div className="bg-white rounded-lg shadow p-6 max-w-2xl">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
                <input type="text" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="smtp.example.com" />
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
                <input type="email" value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="noreply@example.com" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={handleSaveSmtp} className="px-4 py-2 bg-bioaf-600 text-white rounded hover:bg-bioaf-700">
                Save SMTP Settings
              </button>
              <button onClick={handleTestEmail} className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50">
                Send Test Email
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
