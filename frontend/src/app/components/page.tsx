"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ComponentCatalog } from "@/components/components/ComponentCatalog";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ComponentState } from "@/lib/types";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

export default function ComponentsPage() {
  const router = useRouter();
  const [components, setComponents] = useState<ComponentState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    fetchComponents();
  }, [router]);

  const fetchComponents = async () => {
    try {
      const data = await api.get<{ components: ComponentState[] }>("/api/components");
      setComponents(data.components);
    } catch {
      // handled by api client
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Components</h1>
          {loading ? (
            <LoadingSpinner size="lg" />
          ) : (
            <ComponentCatalog components={components} onRefresh={fetchComponents} />
          )}
        </main>
      </div>
    </div>
  );
}
