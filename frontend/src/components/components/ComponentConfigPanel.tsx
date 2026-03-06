"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TerraformPlanViewer } from "./TerraformPlanViewer";
import { api } from "@/lib/api";
import type { ComponentState, TerraformRun } from "@/lib/types";

interface ComponentConfigPanelProps {
  component: ComponentState;
  onUpdate: () => void;
}

export function ComponentConfigPanel({ component, onUpdate }: ComponentConfigPanelProps) {
  const [config, setConfig] = useState<Record<string, unknown>>(component.config);
  const [planRun, setPlanRun] = useState<TerraformRun | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handlePreview = async () => {
    setError("");
    setSaving(true);
    try {
      const result = await api.patch<{
        terraform_run_id: number;
        plan_summary: TerraformRun["plan_summary"];
        component: ComponentState;
      }>(`/api/components/${component.key}/configure`, { config });

      setPlanRun({
        id: result.terraform_run_id,
        plan_summary: result.plan_summary,
        status: "awaiting_confirmation",
      } as TerraformRun);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to preview changes");
    } finally {
      setSaving(false);
    }
  };

  const handleApply = async () => {
    if (!planRun) return;
    setError("");
    try {
      await api.post(`/api/terraform/runs/${planRun.id}/confirm`);
      setPlanRun(null);
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply changes");
    }
  };

  const handleCancel = async () => {
    if (!planRun) return;
    try {
      await api.post(`/api/terraform/runs/${planRun.id}/cancel`);
      setPlanRun(null);
    } catch {
      // ignore
    }
  };

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold">{component.name}</h1>
        <StatusBadge status={component.status} />
      </div>
      <p className="text-gray-600 mb-6">{component.description}</p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Configuration</h2>
        {Object.keys(config).length === 0 ? (
          <p className="text-gray-500 text-sm">No configurable options for this component.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(config).map(([key, value]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{key}</label>
                <input
                  type={typeof value === "number" ? "number" : typeof value === "boolean" ? "checkbox" : "text"}
                  value={typeof value === "boolean" ? undefined : String(value)}
                  checked={typeof value === "boolean" ? value as boolean : undefined}
                  onChange={(e) => {
                    const newVal = typeof value === "number"
                      ? Number(e.target.value)
                      : typeof value === "boolean"
                        ? e.target.checked
                        : e.target.value;
                    setConfig({ ...config, [key]: newVal });
                  }}
                  className="px-3 py-2 border rounded focus:ring-2 focus:ring-bioaf-500"
                />
              </div>
            ))}
          </div>
        )}
        <button
          onClick={handlePreview}
          disabled={saving}
          className="mt-4 px-4 py-2 bg-bioaf-600 text-white rounded hover:bg-bioaf-700 disabled:opacity-50"
        >
          {saving ? "Generating plan..." : "Preview Changes"}
        </button>
      </div>

      {planRun && (
        <TerraformPlanViewer
          planSummary={planRun.plan_summary}
          onApply={handleApply}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}
