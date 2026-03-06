"use client";

import type { ExperimentStatus } from "@/lib/types";

const statusConfig: Record<ExperimentStatus, { label: string; className: string }> = {
  registered: { label: "Registered", className: "bg-gray-100 text-gray-800" },
  library_prep: { label: "Library Prep", className: "bg-blue-100 text-blue-800" },
  sequencing: { label: "Sequencing", className: "bg-indigo-100 text-indigo-800" },
  fastq_uploaded: { label: "FASTQ Uploaded", className: "bg-purple-100 text-purple-800" },
  processing: { label: "Processing", className: "bg-yellow-100 text-yellow-800" },
  pipeline_complete: { label: "Pipeline Complete", className: "bg-teal-100 text-teal-800" },
  reviewed: { label: "Reviewed", className: "bg-cyan-100 text-cyan-800" },
  analysis: { label: "Analysis", className: "bg-orange-100 text-orange-800" },
  complete: { label: "Complete", className: "bg-green-100 text-green-800" },
};

export function ExperimentStatusBadge({ status }: { status: ExperimentStatus }) {
  const config = statusConfig[status] || { label: status, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
