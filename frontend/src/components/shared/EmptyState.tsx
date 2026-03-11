"use client";

import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: "experiments" | "pipelines" | "files" | "default";
  title: string;
  description: string;
  action?: ReactNode;
}

function IconSvg({ icon }: { icon: string }) {
  const className = "w-12 h-12 text-gray-300";

  switch (icon) {
    case "experiments":
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.75 3v3.75m4.5-3.75v3.75M9.75 6.75h4.5m-4.5 0L6 20.25h12L14.25 6.75"
          />
        </svg>
      );
    case "pipelines":
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z"
          />
        </svg>
      );
    case "files":
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
          />
        </svg>
      );
    default:
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 13.5h3.86a2.25 2.25 0 012.012 1.244l.256.512a2.25 2.25 0 002.013 1.244h3.218a2.25 2.25 0 002.013-1.244l.256-.512a2.25 2.25 0 012.013-1.244h3.859M12 3v8.25m0 0l-3-3m3 3l3-3"
          />
        </svg>
      );
  }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center py-12 px-4 text-center"
    >
      {icon !== undefined && <IconSvg icon={icon} />}
      <h3
        data-testid="empty-state-title"
        className="mt-4 text-lg font-semibold text-gray-700"
      >
        {title}
      </h3>
      <p
        data-testid="empty-state-description"
        className="mt-1 text-sm text-gray-500 max-w-sm"
      >
        {description}
      </p>
      {action && (
        <div data-testid="empty-state-action" className="mt-6">
          {action}
        </div>
      )}
    </div>
  );
}
