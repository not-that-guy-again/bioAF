"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ControlledVocabularyValue } from "@/lib/types";

const cache = new Map<string, { data: ControlledVocabularyValue[]; ts: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useVocabulary(fieldName: string) {
  const [values, setValues] = useState<ControlledVocabularyValue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cached = cache.get(fieldName);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      setValues(cached.data);
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const data = await api.get<ControlledVocabularyValue[]>(
          `/api/vocabularies?field=${encodeURIComponent(fieldName)}&active_only=true`
        );
        cache.set(fieldName, { data, ts: Date.now() });
        setValues(data);
      } catch {
        // ignore - field may not have vocabulary values yet
      } finally {
        setLoading(false);
      }
    })();
  }, [fieldName]);

  return { values, loading };
}
