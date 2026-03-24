import { redirect } from "next/navigation";

/**
 * Infrastructure environments page now redirects to the unified
 * environments page (ADR-033 versioned compute environments).
 */
export default function InfrastructureEnvironmentsRedirect() {
  redirect("/environments");
}
