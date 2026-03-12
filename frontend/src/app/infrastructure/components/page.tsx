"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ComponentCatalog } from "@/components/components/ComponentCatalog";
import { StorageSection } from "@/components/components/StorageSection";
import { BootstrapCard } from "@/components/infrastructure/BootstrapCard";
import { TerraformProgressModal } from "@/components/infrastructure/TerraformProgressModal";
import { TerraformRunHistory } from "@/components/infrastructure/TerraformRunHistory";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";

interface TerraformStatus {
  terraform_initialized: boolean;
  terraform_state_bucket: string;
  gcp_credentials_configured: boolean;
  active_run_id: number | null;
  active_run_status: string | null;
}

interface TerraformRun {
  id: number;
  action: string;
  module_name: string | null;
  status: string;
  resources_planned: number | null;
  resources_completed: number;
  triggered_by_user_id: number;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  plan_json: object | null;
  terraform_state_url: string | null;
}

export default function InfraComponentsPage() {
  const router = useRouter();
  const [refreshKey, setRefreshKey] = useState(0);
  const [tfStatus, setTfStatus] = useState<TerraformStatus | null>(null);
  const [runs, setRuns] = useState<TerraformRun[]>([]);
  const [showBootstrapModal, setShowBootstrapModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadTerraformStatus();
  }, [router, refreshKey]);

  async function loadTerraformStatus() {
    try {
      const status = await api.get<TerraformStatus>("/api/v1/infrastructure/terraform/status");
      setTfStatus(status);
      const runsData = await api.get<{ runs: TerraformRun[] }>("/api/v1/infrastructure/terraform/runs");
      setRuns(runsData.runs);
    } catch {
      // non-admin users won't have access - silently skip
    }
  }

  function handleBootstrapComplete() {
    setShowBootstrapModal(false);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Components</h1>

          {tfStatus && (
            <BootstrapCard
              terraformInitialized={tfStatus.terraform_initialized}
              gcpCredentialsConfigured={tfStatus.gcp_credentials_configured}
              onBootstrapStart={() => setShowBootstrapModal(true)}
            />
          )}

          <ComponentCatalog
            key={refreshKey}
            onRefresh={() => setRefreshKey((k) => k + 1)}
          />

          <div className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Storage</h2>
            <StorageSection />
          </div>

          <div className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Recent Operations</h2>
            <TerraformRunHistory runs={runs} />
          </div>
        </main>
      </div>

      {showBootstrapModal && (
        <TerraformProgressModal
          title="Initialize Infrastructure"
          sseUrl="/api/v1/infrastructure/terraform/bootstrap"
          onComplete={handleBootstrapComplete}
          onClose={() => setShowBootstrapModal(false)}
        />
      )}
    </div>
  );
}
