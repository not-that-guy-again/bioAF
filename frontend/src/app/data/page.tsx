"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export default function DataPage() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-white rounded-lg shadow p-12 max-w-md">
              <h1 className="text-2xl font-bold text-gray-400 mb-4">Data</h1>
              <p className="text-gray-400">Coming in Phase 2</p>
              <p className="text-sm text-gray-300 mt-2">
                Data upload, file browser, and metadata management will be available here.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
