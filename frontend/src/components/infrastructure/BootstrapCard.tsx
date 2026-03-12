"use client";

interface BootstrapCardProps {
  terraformInitialized: boolean;
  gcpCredentialsConfigured: boolean;
  onBootstrapStart: () => void;
}

export function BootstrapCard({
  terraformInitialized,
  gcpCredentialsConfigured,
  onBootstrapStart,
}: BootstrapCardProps) {
  if (terraformInitialized) {
    return null;
  }

  return (
    <div
      data-testid="bootstrap-card"
      className="border border-blue-200 bg-blue-50 rounded-xl p-5 mb-6"
    >
      <h3 className="font-semibold text-blue-900 mb-1">Initialize Infrastructure</h3>
      <p className="text-sm text-blue-700 mb-4">
        Create the Terraform state bucket to enable infrastructure provisioning. This runs
        a one-time bootstrap that creates a GCS bucket for storing Terraform state.
      </p>

      {!gcpCredentialsConfigured && (
        <p className="text-sm text-amber-700 mb-3">
          GCP credentials must be configured before initializing.{" "}
          <a
            data-testid="gcp-settings-link"
            href="/settings/gcp"
            className="underline font-medium"
          >
            Configure GCP Settings
          </a>
        </p>
      )}

      <button
        data-testid="bootstrap-btn"
        disabled={!gcpCredentialsConfigured}
        onClick={onBootstrapStart}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                   hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Initialize Infrastructure
      </button>
    </div>
  );
}
