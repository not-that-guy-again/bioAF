"use client";

import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";

interface SlackStatus {
  connected: boolean;
  team_name: string | null;
  team_id: string | null;
  installed_by: string | null;
  installed_at: string | null;
  enabled: boolean;
}

interface SlackChannel {
  id: string;
  name: string;
  is_private: boolean;
}

interface ChannelMapping {
  id: number;
  channel_id: string;
  channel_name: string;
  event_types_json: string[];
  enabled: boolean;
}

const EVENT_CATEGORIES: Record<string, { label: string; events: string[] }> = {
  pipelines: {
    label: "Pipelines & Analysis",
    events: [
      "pipeline.completed",
      "pipeline.failed",
      "pipeline.stage_error",
      "pipeline.run_reviewed",
      "pipeline.run_review_reminder",
      "qc.results_ready",
    ],
  },
  experiments: {
    label: "Experiments & Data",
    events: [
      "experiment.status_changed",
      "results.published",
      "data.uploaded",
      "reference.deprecated",
    ],
  },
  ingest: {
    label: "Ingest & Files",
    events: [
      "ingest.files_cataloged",
      "ingest.unclaimed_entity",
      "ingest.unmatched_file",
      "ingest.duplicate_file",
      "ingest.failure",
      "ingest.batch_complete",
    ],
  },
  infrastructure: {
    label: "Infrastructure",
    events: [
      "compute.node_failure",
      "component.health_degraded",
      "component.health_down",
      "backup.failure",
      "terraform.apply_failure",
      "work_node.heartbeat_timeout",
    ],
  },
  budget: {
    label: "Budget & Storage",
    events: [
      "budget.threshold_50",
      "budget.threshold_80",
      "budget.threshold_100",
      "quota.warning",
      "storage.threshold",
    ],
  },
  automation: {
    label: "Automation",
    events: [
      "trigger.auto_run_submitted",
      "trigger.run_queued_budget",
      "trigger.run_queued_exhausted",
      "trigger.evaluation_failed",
      "trigger.batch_window_closed",
    ],
  },
};

export default function SettingsSlackPage() {
  const [status, setStatus] = useState<SlackStatus | null>(null);
  const [channels, setChannels] = useState<SlackChannel[]>([]);
  const [mappings, setMappings] = useState<ChannelMapping[]>([]);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    try {
      const data = await api.get<SlackStatus>("/api/notifications/slack/status");
      setStatus(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  const loadChannels = useCallback(async () => {
    try {
      const data = await api.get<SlackChannel[]>("/api/notifications/slack/channels");
      setChannels(data);
    } catch {
      // Not connected or error
    }
  }, []);

  const loadMappings = useCallback(async () => {
    try {
      const data = await api.get<ChannelMapping[]>("/api/notifications/slack/channel-mappings");
      setMappings(data);
    } catch {
      // Not connected
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const st = await loadStatus();
      if (st?.connected) {
        await Promise.all([loadChannels(), loadMappings()]);
      }
      setLoading(false);
    };
    init();
  }, [loadStatus, loadChannels, loadMappings]);

  // Handle OAuth callback redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected") === "true") {
      setMessage("Slack connected successfully");
      window.history.replaceState({}, "", "/settings/slack");
      loadStatus().then((st) => {
        if (st?.connected) {
          loadChannels();
          loadMappings();
        }
      });
    }
  }, [loadStatus, loadChannels, loadMappings]);

  const handleConnect = async () => {
    setConnecting(true);
    setError("");
    try {
      const data = await api.get<{ auth_url: string }>("/api/notifications/slack/auth-url");
      window.location.href = data.auth_url;
    } catch {
      setError("Failed to start Slack connection. Ensure BIOAF_SLACK_CLIENT_ID is configured.");
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setError("");
    try {
      await api.delete("/api/notifications/slack/disconnect");
      setStatus({ connected: false, team_name: null, team_id: null, installed_by: null, installed_at: null, enabled: false });
      setChannels([]);
      setMappings([]);
      setMessage("Slack disconnected");
    } catch {
      setError("Failed to disconnect Slack");
    }
  };

  const handleAddMapping = async () => {
    if (!selectedChannel) return;
    setError("");
    const channel = channels.find((c) => c.id === selectedChannel);
    if (!channel) return;

    try {
      const mapping = await api.post<ChannelMapping>("/api/notifications/slack/channel-mappings", {
        channel_id: channel.id,
        channel_name: `#${channel.name}`,
        event_types: selectedEvents,
      });
      setMappings([...mappings, mapping]);
      setSelectedChannel("");
      setSelectedEvents([]);
      setMessage(`Added #${channel.name}`);
    } catch {
      setError("Failed to add channel mapping");
    }
  };

  const handleDeleteMapping = async (id: number) => {
    try {
      await api.delete(`/api/notifications/slack/channel-mappings/${id}`);
      setMappings(mappings.filter((m) => m.id !== id));
      setMessage("Channel mapping removed");
    } catch {
      setError("Failed to remove channel mapping");
    }
  };

  const handleToggleMapping = async (mapping: ChannelMapping) => {
    try {
      const updated = await api.put<ChannelMapping>(`/api/notifications/slack/channel-mappings/${mapping.id}`, {
        enabled: !mapping.enabled,
      });
      setMappings(mappings.map((m) => (m.id === mapping.id ? updated : m)));
    } catch {
      setError("Failed to update channel mapping");
    }
  };

  const handleTestSlack = async () => {
    try {
      await api.post("/api/notifications/test", { channel: "slack" });
      setMessage("Test notification sent to all mapped channels");
    } catch {
      setError("Failed to send test notification");
    }
  };

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  const toggleCategory = (events: string[]) => {
    const allSelected = events.every((e) => selectedEvents.includes(e));
    if (allSelected) {
      setSelectedEvents((prev) => prev.filter((e) => !events.includes(e)));
    } else {
      setSelectedEvents((prev) => [...new Set([...prev, ...events])]);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <p className="text-gray-500">Loading Slack settings...</p>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold">Slack Integration</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Connect your Slack workspace to receive bioAF notifications in channels you choose.
                </p>
              </div>
              {status?.connected && (
                <button
                  onClick={handleTestSlack}
                  className="text-sm text-bioaf-600 hover:text-bioaf-700"
                >
                  Send Test Notification
                </button>
              )}
            </div>

            {message && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">
                {message}
              </div>
            )}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
                {error}
              </div>
            )}

            {/* Connection Status */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="font-semibold mb-4">Connection</h2>
              {status?.connected ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <div>
                      <p className="font-medium">{status.team_name}</p>
                      <p className="text-xs text-gray-500">
                        Connected by {status.installed_by}
                        {status.installed_at && ` on ${new Date(status.installed_at).toLocaleDateString()}`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleDisconnect}
                    className="text-sm text-red-500 hover:text-red-700"
                  >
                    Disconnect
                  </button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-4">
                    Connect bioAF to your Slack workspace to send notifications to channels.
                  </p>
                  <button
                    onClick={handleConnect}
                    disabled={connecting}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#4A154B] text-white rounded-lg hover:bg-[#3a1039] disabled:opacity-50 font-medium"
                  >
                    <svg width="20" height="20" viewBox="0 0 54 54" xmlns="http://www.w3.org/2000/svg">
                      <path d="M19.712.133a5.381 5.381 0 0 0-5.376 5.387 5.381 5.381 0 0 0 5.376 5.386h5.376V5.52A5.381 5.381 0 0 0 19.712.133m0 14.365H5.376A5.381 5.381 0 0 0 0 19.884a5.381 5.381 0 0 0 5.376 5.387h14.336a5.381 5.381 0 0 0 5.376-5.387 5.381 5.381 0 0 0-5.376-5.386" fill="#36C5F0"/>
                      <path d="M53.76 19.884a5.381 5.381 0 0 0-5.376-5.386 5.381 5.381 0 0 0-5.376 5.386v5.387h5.376a5.381 5.381 0 0 0 5.376-5.387m-14.336 0V5.52A5.381 5.381 0 0 0 34.048.133a5.381 5.381 0 0 0-5.376 5.387v14.364a5.381 5.381 0 0 0 5.376 5.387 5.381 5.381 0 0 0 5.376-5.387" fill="#2EB67D"/>
                      <path d="M34.048 54a5.381 5.381 0 0 0 5.376-5.387 5.381 5.381 0 0 0-5.376-5.386h-5.376v5.386A5.381 5.381 0 0 0 34.048 54m0-14.365h14.336a5.381 5.381 0 0 0 5.376-5.386 5.381 5.381 0 0 0-5.376-5.387H34.048a5.381 5.381 0 0 0-5.376 5.387 5.381 5.381 0 0 0 5.376 5.386" fill="#ECB22E"/>
                      <path d="M0 34.249a5.381 5.381 0 0 0 5.376 5.386 5.381 5.381 0 0 0 5.376-5.386v-5.387H5.376A5.381 5.381 0 0 0 0 34.25m14.336-.001v14.364A5.381 5.381 0 0 0 19.712 54a5.381 5.381 0 0 0 5.376-5.387V34.249a5.381 5.381 0 0 0-5.376-5.387 5.381 5.381 0 0 0-5.376 5.387" fill="#E01E5A"/>
                    </svg>
                    {connecting ? "Connecting..." : "Add to Slack"}
                  </button>
                </div>
              )}
            </div>

            {/* Channel Mappings (only when connected) */}
            {status?.connected && (
              <>
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                  <h2 className="font-semibold mb-4">Channel Mappings</h2>
                  <p className="text-sm text-gray-500 mb-4">
                    Route notifications to specific Slack channels. Leave event types empty to receive all events.
                  </p>

                  {mappings.length > 0 && (
                    <div className="space-y-2 mb-6">
                      {mappings.map((mapping) => (
                        <div
                          key={mapping.id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded"
                        >
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleToggleMapping(mapping)}
                              className={`w-8 h-5 rounded-full relative transition-colors ${
                                mapping.enabled ? "bg-bioaf-600" : "bg-gray-300"
                              }`}
                            >
                              <span
                                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                                  mapping.enabled ? "left-3.5" : "left-0.5"
                                }`}
                              />
                            </button>
                            <div>
                              <span className="font-medium text-sm">{mapping.channel_name}</span>
                              {mapping.event_types_json.length > 0 ? (
                                <span className="ml-2 text-xs text-gray-500">
                                  {mapping.event_types_json.length} event type{mapping.event_types_json.length !== 1 ? "s" : ""}
                                </span>
                              ) : (
                                <span className="ml-2 text-xs text-gray-500">All events</span>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteMapping(mapping.id)}
                            className="text-xs text-red-500 hover:text-red-700"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add new mapping */}
                  <div className="border-t pt-4">
                    <h3 className="font-medium text-sm mb-3">Add Channel</h3>
                    <div className="flex gap-3 mb-4">
                      <select
                        value={selectedChannel}
                        onChange={(e) => setSelectedChannel(e.target.value)}
                        className="flex-1 px-3 py-2 border rounded text-sm"
                      >
                        <option value="">Select a channel...</option>
                        {channels
                          .filter((ch) => !mappings.some((m) => m.channel_id === ch.id))
                          .map((ch) => (
                            <option key={ch.id} value={ch.id}>
                              {ch.is_private ? "🔒 " : "#"}{ch.name}
                            </option>
                          ))}
                      </select>
                      <button
                        onClick={handleAddMapping}
                        disabled={!selectedChannel}
                        className="px-4 py-2 bg-bioaf-600 text-white rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                      >
                        Add
                      </button>
                    </div>

                    {/* Event type filter */}
                    {selectedChannel && (
                      <div className="bg-gray-50 rounded p-4">
                        <p className="text-xs text-gray-500 mb-3">
                          Select event types for this channel (leave all unchecked for all events):
                        </p>
                        <div className="space-y-4">
                          {Object.entries(EVENT_CATEGORIES).map(([key, category]) => {
                            const allSelected = category.events.every((e) =>
                              selectedEvents.includes(e)
                            );
                            const someSelected = category.events.some((e) =>
                              selectedEvents.includes(e)
                            );
                            return (
                              <div key={key}>
                                <label className="flex items-center gap-2 text-sm font-medium mb-1 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={allSelected}
                                    ref={(el) => {
                                      if (el) el.indeterminate = someSelected && !allSelected;
                                    }}
                                    onChange={() => toggleCategory(category.events)}
                                    className="rounded"
                                  />
                                  {category.label}
                                </label>
                                <div className="ml-6 flex flex-wrap gap-x-4 gap-y-1">
                                  {category.events.map((event) => (
                                    <label
                                      key={event}
                                      className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer"
                                    >
                                      <input
                                        type="checkbox"
                                        checked={selectedEvents.includes(event)}
                                        onChange={() => toggleEvent(event)}
                                        className="rounded"
                                      />
                                      {event.split(".").pop()?.replace(/_/g, " ")}
                                    </label>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
