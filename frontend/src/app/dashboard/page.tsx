"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { isAuthenticated } from "@/lib/auth";
import { InfrastructureHealthWidget } from "@/components/dashboard/InfrastructureHealthWidget";
import { RunningJobsWidget } from "@/components/dashboard/RunningJobsWidget";
import { QueueDepthWidget } from "@/components/dashboard/QueueDepthWidget";
import { CostBudgetWidget } from "@/components/dashboard/CostBudgetWidget";
import { IngestStatusWidget } from "@/components/dashboard/IngestStatusWidget";
import { ActivityFeedWidget } from "@/components/dashboard/ActivityFeedWidget";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <Breadcrumb />
        <main className="flex-1 overflow-y-auto p-6" data-testid="dashboard">
          <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <InfrastructureHealthWidget />
            <RunningJobsWidget />
            <QueueDepthWidget />
            <CostBudgetWidget />
            <IngestStatusWidget />
          </div>

          <ActivityFeedWidget />
        </main>
      </div>
    </div>
  );
}
