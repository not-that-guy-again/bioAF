"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ComponentState } from "@/lib/types";

export function useComponents() {
  const [components, setComponents] = useState<ComponentState[]>([]);
  const [loading, setLoading] = useState(true);

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

  useEffect(() => {
    fetchComponents();
  }, []);

  return { components, loading, refetch: fetchComponents };
}
