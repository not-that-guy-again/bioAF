"use client";

import { useEffect, useState } from "react";
import type { ComponentState } from "@/lib/types";
import { ComponentCard } from "./ComponentCard";
import { api } from "@/lib/api";

// Components that are only available with the SLURM compute stack
const SLURM_ONLY_COMPONENTS = ["slurm_cluster", "filestore", "slurm_autoscaler"];

// Components specific to the Kubernetes compute stack
const K8S_COMPONENTS = ["k8s_pipeline_pool", "k8s_interactive_pool", "gke_cluster"];

interface ComponentCatalogProps {
  components: ComponentState[];
  onRefresh: () => void;
}

export function ComponentCatalog({ components, onRefresh }: ComponentCatalogProps) {
  const [computeStack, setComputeStack] = useState("kubernetes");

  useEffect(() => {
    api
      .get<{ compute_stack: string }>("/api/v1/infrastructure/compute/stack")
      .then((data) => setComputeStack(data.compute_stack))
      .catch(() => {
        // Default to kubernetes if endpoint unavailable
      });
  }, []);

  const categories = [...new Set(components.map((c) => c.category))];

  return (
    <div className="space-y-8">
      {categories.map((category) => (
        <div key={category}>
          <h2 className="text-lg font-semibold capitalize mb-4">{category}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {components
              .filter((c) => c.category === category)
              .map((comp) => {
                const isSlurmOnly = SLURM_ONLY_COMPONENTS.includes(comp.key);
                const isK8sOnly = K8S_COMPONENTS.includes(comp.key);
                const comingSoon =
                  (computeStack === "kubernetes" && isSlurmOnly) ||
                  (computeStack === "slurm" && isK8sOnly);

                return (
                  <ComponentCard
                    key={comp.key}
                    component={comp}
                    onAction={onRefresh}
                    comingSoon={comingSoon}
                    comingSoonMessage={
                      comingSoon
                        ? computeStack === "kubernetes"
                          ? "Coming Soon — available with SLURM compute stack"
                          : "Coming Soon — available with Kubernetes compute stack"
                        : undefined
                    }
                  />
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
}
