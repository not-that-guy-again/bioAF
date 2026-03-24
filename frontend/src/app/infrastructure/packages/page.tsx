import { redirect } from "next/navigation";

/**
 * Infrastructure packages page now redirects to the unified
 * environments page (ADR-033 versioned compute environments).
 */
export default function InfraPackagesRedirect() {
  redirect("/environments");
}
