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

  return (
    <div className="flex items-center justify-center h-screen text-gray-400 text-sm">
      Redirecting to Environments...
    </div>
  );
}
