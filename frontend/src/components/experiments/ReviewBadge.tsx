"use client";

import type { ReviewVerdict } from "@/lib/types";

const verdictConfig: Record<ReviewVerdict, { label: string; className: string }> = {
  approved: { label: "Approved", className: "bg-green-100 text-green-800" },
  approved_with_caveats: { label: "Approved w/ Caveats", className: "bg-yellow-100 text-yellow-800" },
  rejected: { label: "Rejected", className: "bg-red-100 text-red-800" },
  revision_requested: { label: "Revision Requested", className: "bg-orange-100 text-orange-800" },
};

interface ReviewBadgeProps {
  verdict: ReviewVerdict;
  size?: "sm" | "md";
}

export function ReviewBadge({ verdict, size = "sm" }: ReviewBadgeProps) {
  const config = verdictConfig[verdict] || { label: verdict, className: "bg-gray-100 text-gray-600" };
  const sizeClass = size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span className={`inline-flex items-center rounded font-medium ${sizeClass} ${config.className}`}>
      {config.label}
    </span>
  );
}
