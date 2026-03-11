"use client";

interface LoadingStateProps {
  message?: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "w-5 h-5 border-2",
  md: "w-8 h-8 border-[3px]",
  lg: "w-12 h-12 border-4",
};

const textSizeClasses = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-base",
};

export function LoadingState({
  message = "Loading...",
  size = "md",
}: LoadingStateProps) {
  return (
    <div
      data-testid="loading-state"
      className="flex flex-col items-center justify-center py-12 px-4"
    >
      <div
        data-testid="loading-spinner"
        className={`${sizeClasses[size]} rounded-full border-gray-200 border-t-bioaf-600 animate-spin`}
      />
      {message && (
        <p
          data-testid="loading-message"
          className={`mt-3 text-gray-500 ${textSizeClasses[size]}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
