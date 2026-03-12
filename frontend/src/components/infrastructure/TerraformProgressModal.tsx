"use client";

import { useEffect, useRef, useState } from "react";

interface TerraformEvent {
  event_type: string;
  message: string;
  resource_address?: string;
  resources_completed?: number;
  resources_total?: number;
  log_line?: string;
}

interface TerraformProgressModalProps {
  title: string;
  sseUrl: string;
  onComplete: () => void;
  onClose: () => void;
}

type ModalStatus = "connecting" | "running" | "complete" | "error";

export function TerraformProgressModal({
  title,
  sseUrl,
  onComplete,
  onClose,
}: TerraformProgressModalProps) {
  const [status, setStatus] = useState<ModalStatus>("connecting");
  const [events, setEvents] = useState<TerraformEvent[]>([]);
  const [resourcesCompleted, setResourcesCompleted] = useState(0);
  const [resourcesTotal, setResourcesTotal] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [showLog, setShowLog] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(sseUrl);
    esRef.current = es;
    setStatus("running");

    es.onmessage = (ev: MessageEvent) => {
      try {
        const event: TerraformEvent = JSON.parse(ev.data);
        setEvents((prev) => [...prev, event]);

        if (event.resources_total) {
          setResourcesTotal(event.resources_total);
        }
        if (event.resources_completed !== undefined) {
          setResourcesCompleted(event.resources_completed);
        }
        if (event.log_line) {
          setLogLines((prev) => [...prev, event.log_line!]);
        }

        if (event.event_type === "apply_complete") {
          setStatus("complete");
          es.close();
        } else if (event.event_type === "apply_error") {
          setStatus("error");
          setErrorMessage(event.message);
          es.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setStatus("error");
      setErrorMessage("Connection to server lost");
      es.close();
    };

    return () => {
      es.close();
    };
  }, [sseUrl]);

  const progressPct =
    resourcesTotal > 0 ? Math.round((resourcesCompleted / resourcesTotal) * 100) : 0;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>

        <div data-testid="tf-modal-status" className="mb-4">
          {status === "connecting" && (
            <p className="text-sm text-gray-500">Connecting...</p>
          )}
          {status === "running" && (
            <p className="text-sm text-blue-600 flex items-center gap-2">
              <span className="inline-block h-3 w-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              Running...
            </p>
          )}
          {status === "complete" && (
            <p className="text-sm text-green-600 font-medium">Complete</p>
          )}
          {status === "error" && (
            <p data-testid="tf-modal-error" className="text-sm text-red-600 font-medium">
              Error: {errorMessage}
            </p>
          )}
        </div>

        {resourcesTotal > 0 && (
          <div data-testid="tf-progress-bar" className="mb-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>
                {resourcesCompleted} / {resourcesTotal} resources
              </span>
              <span>{progressPct}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}

        {events.length > 0 && (
          <ul className="space-y-1 mb-4 max-h-40 overflow-y-auto">
            {events
              .filter((e) => e.event_type === "resource_complete")
              .map((e, i) => (
                <li key={i} className="text-sm flex items-center gap-2">
                  <span className="text-green-500">&#10003;</span>
                  <span className="text-gray-700">{e.message}</span>
                </li>
              ))}
          </ul>
        )}

        {logLines.length > 0 && (
          <div className="mb-4">
            <button
              onClick={() => setShowLog((v) => !v)}
              className="text-xs text-gray-500 underline"
            >
              {showLog ? "Hide" : "Show"} log
            </button>
            {showLog && (
              <pre className="mt-2 text-xs bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
                {logLines.join("\n")}
              </pre>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          {status === "complete" && (
            <button
              data-testid="tf-modal-done-btn"
              onClick={() => {
                onComplete();
                onClose();
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
            >
              Done
            </button>
          )}
          {status === "error" && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300"
            >
              Close
            </button>
          )}
          {(status === "connecting" || status === "running") && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
