"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ComponentConfigPanel } from "@/components/components/ComponentConfigPanel";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ComponentState } from "@/lib/types";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

export default function ComponentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const [component, setComponent] = useState<ComponentState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    fetchComponent();
  }, [router, id]);

  const fetchComponent = async () => {
    try {
      const data = await api.get<ComponentState>(`/api/components/${id}`);
      setComponent(data);
    } catch {
      // handled
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
          {loading ? (
            <LoadingSpinner size="lg" />
          ) : component ? (
            <ComponentConfigPanel component={component} onUpdate={fetchComponent} />
          ) : (
            <p className="text-gray-500">Component not found</p>
          )}
        </main>
      </div>
    </div>
  );
}
