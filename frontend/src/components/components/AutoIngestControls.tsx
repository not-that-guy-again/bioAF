"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface AutoIngestStatus {
  enabled: boolean;
  cleanup_policy: string;
  listener_running: boolean;
  pubsub_topic: string | null;
  pubsub_subscription: string | null;
  messages_processed_24h: number;
  messages_failed_24h: number;
}

interface AutoIngestControlsProps {
  storageDeployed: boolean;
  pubsubConfigured: boolean;
  onUpdateStorage?: () => void;
}

export function AutoIngestControls({
  storageDeployed,
  pubsubConfigured,
  onUpdateStorage,
}: AutoIngestControlsProps) {
  const [status, setStatus] = useState<AutoIngestStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!storageDeployed || !pubsubConfigured) return;
    api
      .get<AutoIngestStatus>("/api/v1/settings/auto-ingest")
      .then(setStatus)
      .catch(() => {});
  }, [storageDeployed, pubsubConfigured]);

  if (!storageDeployed) return null;

  if (!pubsubConfigured) {
    return (
      <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded text-sm">
        <p className="text-amber-800 font-medium text-xs">
          Auto-ingest requires an infrastructure update. Click to deploy the
          notification system.
        </p>
        <button
          onClick={onUpdateStorage}
          className="mt-2 px-3 py-1.5 bg-amber-600 text-white rounded text-xs hover:bg-amber-700"
        >
          Update Storage Infrastructure
        </button>
      </div>
    );
  }

  const handleToggle = async () => {
    const newEnabled = !status?.enabled;
    setLoading(true);
    try {
      await api.post("/api/v1/settings/auto-ingest", {
        enabled: newEnabled,
        cleanup_policy: status?.cleanup_policy || "delete_after_copy",
      });
      const updated = await api.get<AutoIngestStatus>(
        "/api/v1/settings/auto-ingest",
      );
      setStatus(updated);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handlePolicyChange = async (policy: string) => {
    setLoading(true);
    try {
      await api.post("/api/v1/settings/auto-ingest", {
        enabled: status?.enabled ?? false,
        cleanup_policy: policy,
      });
      const updated = await api.get<AutoIngestStatus>(
        "/api/v1/settings/auto-ingest",
      );
      setStatus(updated);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const dotColor = status?.enabled
    ? status.listener_running
      ? "bg-green-500"
      : "bg-amber-500"
    : "bg-gray-400";

  const statusText = status?.enabled
    ? status.listener_running
      ? "Active"
      : "Enabled but not running"
    : "Disabled";

  return (
    <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded text-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">
            Auto-Ingest
          </span>
          <span
            data-testid="status-dot"
            className={`inline-block w-2 h-2 rounded-full ${dotColor}`}
          />
          <span className="text-xs text-gray-500">{statusText}</span>
        </div>
        <button
          data-testid="auto-ingest-toggle"
          aria-label="toggle"
          onClick={handleToggle}
          disabled={loading}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            status?.enabled ? "bg-bioaf-600" : "bg-gray-300"
          } ${loading ? "opacity-50" : ""}`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
              status?.enabled ? "translate-x-4" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {status?.enabled && (
        <>
          <div>
            <label
              htmlFor="cleanup-policy"
              className="text-xs text-gray-600 block mb-1"
            >
              Cleanup policy
            </label>
            <select
              id="cleanup-policy"
              data-testid="cleanup-policy-select"
              value={status.cleanup_policy}
              onChange={(e) => handlePolicyChange(e.target.value)}
              disabled={loading}
              className="text-xs border border-gray-300 rounded px-2 py-1 w-full"
            >
              <option value="delete_after_copy">
                Delete after cataloging
              </option>
              <option value="retain_7d">Retain for 7 days</option>
              <option value="retain_30d">Retain for 30 days</option>
            </select>
          </div>

          <div className="flex gap-4 text-xs text-gray-500">
            <span>
              Files ingested (24h):{" "}
              <span className="font-medium text-gray-700">
                {status.messages_processed_24h}
              </span>
            </span>
            <span>
              Failed (24h):{" "}
              <span className="font-medium text-red-600">
                {status.messages_failed_24h}
              </span>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
