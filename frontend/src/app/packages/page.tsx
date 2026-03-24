import { redirect } from "next/navigation";

/**
 * Package management page now redirects to the unified
 * environments page (ADR-033 versioned compute environments).
 */
export default function PackagesRedirect() {
  redirect("/environments");
}
