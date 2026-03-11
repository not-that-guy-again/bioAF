"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export default function PipelineSchedulingPage() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6">
          <h1 className="text-2xl font-bold mb-4">Pipeline Scheduling</h1>
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-400">Coming soon. Pipeline scheduling and cron-based triggers will be available here.</p>
          </div>
        </main>
      </div>
    </div>
  );
}
