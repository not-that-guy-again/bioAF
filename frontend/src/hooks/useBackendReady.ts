"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const POLL_INTERVAL_MS = 2000;

/**
 * Polls the backend health endpoint until it responds successfully.
 * Returns { ready: false } while the backend is unreachable or unhealthy,
 * and { ready: true } once confirmed healthy. Stops polling after that.
 */
export function useBackendReady() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function check() {
      try {
        const res = await fetch(`${API_URL}/api/health/ready`, {
          cache: "no-store",
        });
        if (!cancelled && res.ok) {
          const body = await res.json();
          if (body.status === "ok") {
            setReady(true);
            return;
          }
        }
      } catch {
        // Backend not reachable yet
      }
      if (!cancelled) {
        timer = setTimeout(check, POLL_INTERVAL_MS);
      }
    }

    check();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return { ready };
}
