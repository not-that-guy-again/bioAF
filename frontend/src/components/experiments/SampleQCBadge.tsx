"use client";

import type { QCStatus } from "@/lib/types";

const qcConfig: Record<string, { label: string; className: string }> = {
  pass: { label: "Pass", className: "bg-green-100 text-green-800" },
  warning: { label: "Warning", className: "bg-yellow-100 text-yellow-800" },
  fail: { label: "Fail", className: "bg-red-100 text-red-800" },
};

export function SampleQCBadge({ status }: { status: QCStatus | null }) {
  if (!status) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
        Not Set
      </span>
    );
  }
  const config = qcConfig[status] || { label: status, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
