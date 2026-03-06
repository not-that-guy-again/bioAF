"use client";

import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ComponentState } from "@/lib/types";

interface ComponentInventoryProps {
  components: ComponentState[];
}

export function ComponentInventory({ components }: ComponentInventoryProps) {
  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold">Component Inventory</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Component</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {components.map((comp) => (
              <tr key={comp.key} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="font-medium text-sm">{comp.name}</div>
                  <div className="text-xs text-gray-500">{comp.description}</div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 capitalize">{comp.category}</td>
                <td className="px-6 py-4">
                  <StatusBadge status={comp.status} />
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{comp.estimated_monthly_cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
