const statusColors: Record<string, string> = {
  healthy: "bg-green-100 text-green-800",
  running: "bg-green-100 text-green-800",
  active: "bg-green-100 text-green-800",
  completed: "bg-green-100 text-green-800",
  disabled: "bg-gray-100 text-gray-600",
  provisioning: "bg-yellow-100 text-yellow-800",
  applying: "bg-yellow-100 text-yellow-800",
  pending: "bg-yellow-100 text-yellow-800",
  planning: "bg-yellow-100 text-yellow-800",
  awaiting_confirmation: "bg-blue-100 text-blue-800",
  destroying: "bg-orange-100 text-orange-800",
  error: "bg-red-100 text-red-800",
  failed: "bg-red-100 text-red-800",
  unhealthy: "bg-red-100 text-red-800",
  degraded: "bg-yellow-100 text-yellow-800",
  invited: "bg-blue-100 text-blue-800",
  deactivated: "bg-gray-100 text-gray-600",
  cancelled: "bg-gray-100 text-gray-600",
};

export function StatusBadge({ status }: { status: string }) {
  const colorClass = statusColors[status] || "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
