"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Infrastructure environments page now redirects to the unified
 * environments page (ADR-033 versioned compute environments).
 */
export default function InfrastructureEnvironmentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/environments");
  }, [router]);

  return null;
}
