"use client";

/**
 * Badge component that indicates an entity was auto-created by the ingest
 * pipeline and has not yet been claimed by a user.
 */
export function UnclaimedBadge({ entityType }: { entityType?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200"
      title={`This ${entityType || "entity"} was auto-created by the ingest pipeline and needs to be claimed.`}
    >
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18 9 9 0 000-18z" />
      </svg>
      Unclaimed
    </span>
  );
}
