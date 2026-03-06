"use client";

import type { ComponentState } from "@/lib/types";
import { ComponentCard } from "./ComponentCard";

interface ComponentCatalogProps {
  components: ComponentState[];
  onRefresh: () => void;
}

export function ComponentCatalog({ components, onRefresh }: ComponentCatalogProps) {
  const categories = [...new Set(components.map((c) => c.category))];

  return (
    <div className="space-y-8">
      {categories.map((category) => (
        <div key={category}>
          <h2 className="text-lg font-semibold capitalize mb-4">{category}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {components
              .filter((c) => c.category === category)
              .map((comp) => (
                <ComponentCard key={comp.key} component={comp} onAction={onRefresh} />
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
