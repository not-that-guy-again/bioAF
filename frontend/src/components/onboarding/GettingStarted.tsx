"use client";

import { useCallback, useEffect, useState } from "react";

interface Slide {
  title: string;
  description: string;
  image: string;
}

const SLIDES: Slide[] = [
  { title: "Dashboard", description: "Your home base. See project activity, infrastructure status, and pipeline runs at a glance.", image: "/getting-started/01-dashboard.png" },
  { title: "Active Projects", description: "Track how many projects are currently active and their overall health.", image: "/getting-started/02-active-projects.png" },
  { title: "Recent Pipeline Runs", description: "See the latest pipeline executions and their completion status.", image: "/getting-started/03-recent-pipeline-runs.png" },
  { title: "Infrastructure Status", description: "Monitor your cluster and storage at a glance.", image: "/getting-started/04-infrastructure-status.png" },
  { title: "Cost Tracking", description: "Keep an eye on cloud spending with real-time cost estimates.", image: "/getting-started/05-cost-tracking.png" },
  { title: "Infrastructure Components", description: "View and manage the services running in your cluster.", image: "/getting-started/06-infrastructure-components.png" },
  { title: "Cost Center", description: "Break down cloud costs by service, project, and time period.", image: "/getting-started/07-cost-center.png" },
  { title: "Backup & Recovery", description: "Set up automated backups and test your recovery procedures.", image: "/getting-started/08-backup-recovery.png" },
  { title: "User Management", description: "See who has access and invite new team members.", image: "/getting-started/09-user-management.png" },
  { title: "Roles & Permissions", description: "Control what each role can see and do.", image: "/getting-started/10-roles-permissions.png" },
  { title: "Your Profile", description: "Update your account settings, session credentials, and GitHub integration.", image: "/getting-started/11-your-profile.png" },
  { title: "Projects", description: "Create and manage your research projects.", image: "/getting-started/12-projects.png" },
  { title: "Experiments", description: "Organize your work into experiments within projects.", image: "/getting-started/13-experiments.png" },
  { title: "Pipeline Catalog", description: "Browse and configure available analysis pipelines.", image: "/getting-started/14-pipeline-catalog.png" },
  { title: "Pipeline Runs", description: "Monitor running pipelines and review completed ones.", image: "/getting-started/15-pipeline-runs.png" },
  { title: "QC Dashboards", description: "Review quality control metrics for your data.", image: "/getting-started/16-qc-dashboards.png" },
  { title: "CellxGene", description: "Explore single-cell datasets with the interactive visualizer.", image: "/getting-started/17-cellxgene.png" },
];

interface GettingStartedProps {
  onComplete: () => void;
  standalone?: boolean;
}

export function GettingStarted({ onComplete, standalone }: GettingStartedProps) {
  const [current, setCurrent] = useState(0);
  const isFirst = current === 0;
  const isLast = current === SLIDES.length - 1;
  const slide = SLIDES[current];

  const goNext = useCallback(() => {
    if (!isLast) setCurrent((c) => c + 1);
  }, [isLast]);

  const goPrev = useCallback(() => {
    if (!isFirst) setCurrent((c) => c - 1);
  }, [isFirst]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight") goNext();
      if (e.key === "ArrowLeft") goPrev();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [goNext, goPrev]);

  const finishLabel = standalone ? "Close" : "Go to Dashboard";

  return (
    <div className="flex flex-col items-center max-w-3xl mx-auto">
      {/* Slide content */}
      <div className="w-full mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{slide.title}</h3>
        <p className="text-sm text-gray-600 mb-4">{slide.description}</p>
        <div className="bg-gray-100 border rounded-lg overflow-hidden flex items-center justify-center" style={{ minHeight: 320 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={slide.image} alt={slide.title} className="max-w-full max-h-80 object-contain" />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-4 mb-4">
        <button
          aria-label="Previous slide"
          onClick={goPrev}
          disabled={isFirst}
          className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          &larr;
        </button>

        {isLast ? (
          <button
            onClick={onComplete}
            className="px-4 py-1.5 rounded bg-bioaf-600 text-white hover:bg-bioaf-700"
          >
            {finishLabel}
          </button>
        ) : (
          <button
            aria-label="Next slide"
            onClick={goNext}
            className="px-3 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            &rarr;
          </button>
        )}
      </div>

      {/* Dot indicators */}
      <div className="flex gap-1.5 mb-4">
        {SLIDES.map((_, i) => (
          <button
            key={i}
            data-testid="slide-dot"
            onClick={() => setCurrent(i)}
            className={`w-2 h-2 rounded-full transition-colors ${
              i === current ? "bg-bioaf-600" : "bg-gray-300"
            }`}
          />
        ))}
      </div>

      {/* Skip tour */}
      <button onClick={onComplete} className="text-sm text-gray-500 hover:text-gray-700">
        Skip tour
      </button>
    </div>
  );
}
