"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ComponentCatalog } from "@/components/components/ComponentCatalog";
import { StorageSection } from "@/components/components/StorageSection";
import { isAuthenticated } from "@/lib/auth";

export default function InfraComponentsPage() {
  const router = useRouter();
  const [refreshKey, setRefreshKey] = useState(0);

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
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Components</h1>
          <ComponentCatalog
            key={refreshKey}
            onRefresh={() => setRefreshKey((k) => k + 1)}
          />
          <div className="mt-10">
            <h2 className="text-xl font-semibold mb-4">Storage</h2>
            <StorageSection />
          </div>
        </main>
      </div>
    </div>
  );
}
