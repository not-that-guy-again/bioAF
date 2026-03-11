"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";

interface SlackWebhook {
  id: number;
  name: string;
  webhook_url: string;
  channel_name: string | null;
  event_types_json: string[];
  enabled: boolean;
}

export default function SettingsSlackPage() {
  const [webhooks, setWebhooks] = useState<SlackWebhook[]>([]);
  const [newWebhookName, setNewWebhookName] = useState("");
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [newWebhookChannel, setNewWebhookChannel] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      const data = await api.get<SlackWebhook[]>("/api/notifications/slack-webhooks");
      setWebhooks(data);
    } catch {
      // ignore
    }
  };

  const handleAddWebhook = async () => {
    if (!newWebhookName || !newWebhookUrl) return;
    setError("");
    setMessage("");
    try {
      const wh = await api.post<SlackWebhook>("/api/notifications/slack-webhooks", {
        name: newWebhookName,
        webhook_url: newWebhookUrl,
        channel_name: newWebhookChannel || null,
        event_types: [],
      });
      setWebhooks([...webhooks, wh]);
      setNewWebhookName("");
      setNewWebhookUrl("");
      setNewWebhookChannel("");
      setMessage("Webhook added successfully");
    } catch {
      setError("Failed to add webhook");
    }
  };

  const handleDeleteWebhook = async (id: number) => {
    try {
      await api.delete(`/api/notifications/slack-webhooks/${id}`);
      setWebhooks(webhooks.filter((w) => w.id !== id));
      setMessage("Webhook removed");
    } catch {
      setError("Failed to delete webhook");
    }
  };

  const handleTestSlack = async () => {
    try {
      await api.post("/api/notifications/test", { channel: "slack" });
      setMessage("Test notification sent via Slack");
    } catch {
      setError("Failed to send test notification via Slack");
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">Slack Webhooks</h1>
            <button
              onClick={handleTestSlack}
              className="text-sm text-bioaf-600 hover:text-bioaf-700"
            >
              Send Test Notification
            </button>
          </div>

          {message && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">{message}</div>}
          {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}

          <div className="bg-white rounded-lg shadow p-6">
            {webhooks.length > 0 && (
              <div className="mb-6 space-y-2">
                {webhooks.map((wh) => (
                  <div key={wh.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <span className="font-medium text-sm">{wh.name}</span>
                      {wh.channel_name && (
                        <span className="ml-2 text-xs text-gray-500">{wh.channel_name}</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteWebhook(wh.id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}

            <h3 className="font-medium mb-3">Add Webhook</h3>
            <div className="grid grid-cols-3 gap-3">
              <input
                type="text"
                placeholder="Webhook name"
                value={newWebhookName}
                onChange={(e) => setNewWebhookName(e.target.value)}
                className="px-3 py-2 border rounded text-sm"
              />
              <input
                type="url"
                placeholder="https://hooks.slack.com/..."
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                className="px-3 py-2 border rounded text-sm"
              />
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="#channel"
                  value={newWebhookChannel}
                  onChange={(e) => setNewWebhookChannel(e.target.value)}
                  className="flex-1 px-3 py-2 border rounded text-sm"
                />
                <button
                  onClick={handleAddWebhook}
                  className="px-3 py-2 bg-bioaf-600 text-white rounded text-sm hover:bg-bioaf-700"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
