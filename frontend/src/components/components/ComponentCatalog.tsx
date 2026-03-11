"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ComponentCard } from "./ComponentCard";
import type { ComponentState } from "@/lib/types";

interface ComponentDef {
  key: string;
  name: string;
  category: string;
  description: string;
  cost_estimate: string;
  dependencies: string[];
  configurable_fields: Record<string, unknown>[];
  status: string;
}

interface ComponentsData {
  compute_stack: string;
  components: ComponentDef[];
}

const CATEGORY_LABELS: Record<string, string> = {
  compute: "Compute",
  pipeline_orchestration: "Pipeline Orchestration",
  analysis: "Analysis",
  visualization: "Visualization",
  search: "Search",
};

const CATEGORY_ORDER = [
  "compute",
  "pipeline_orchestration",
  "analysis",
  "visualization",
  "search",
];

function defToState(def: ComponentDef): ComponentState {
  return {
    key: def.key,
    name: def.name,
    description: def.description,
    category: def.category,
    enabled: false,
    status: "disabled",
    config: {},
    dependencies: def.dependencies,
    estimated_monthly_cost: def.cost_estimate,
    updated_at: null,
  };
}

interface ComponentCatalogProps {
  onRefresh: () => void;
}

export function ComponentCatalog({ onRefresh }: ComponentCatalogProps) {
  const [data, setData] = useState<ComponentsData | null>(null);

  useEffect(() => {
    api
      .get<ComponentsData>("/api/v1/infrastructure/components")
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return null;

  const { compute_stack, components } = data;
  const stackLabel =
    compute_stack === "kubernetes" ? "Kubernetes + GCS (Recommended)" : "SLURM + NFS";

  const categories = CATEGORY_ORDER.filter((c) =>
    components.some((comp) => comp.category === c),
  );

  return (
    <div className="space-y-8">
      <div
        data-testid="compute-stack-banner"
        className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3"
      >
        <span className="text-sm font-medium text-blue-700">Compute Stack:</span>
        <span className="text-sm text-blue-900">{stackLabel}</span>
      </div>

      {categories.map((category) => (
        <div key={category}>
          <h2 className="text-lg font-semibold mb-4">
            {CATEGORY_LABELS[category] ?? category}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {components
              .filter((c) => c.category === category)
              .map((comp) => (
                <ComponentCard
                  key={comp.key}
                  component={defToState(comp)}
                  onAction={onRefresh}
                  comingSoon={comp.status === "coming_soon"}
                  comingSoonMessage={
                    comp.status === "coming_soon"
                      ? "Coming Soon — not available with current compute stack"
                      : undefined
                  }
                />
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
