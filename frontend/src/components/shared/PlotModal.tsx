"use client";

import { useEffect } from "react";

interface PlotMetadata {
  experimentName?: string | null;
  projectName?: string | null;
  pipelineRunId?: number | null;
  pipelineRunName?: string | null;
  notebookSessionId?: number | null;
  notebookSessionType?: string | null;
  sourceType?: string | null;
  tags?: string[];
  indexedAt?: string | null;
}

interface PlotModalProps {
  url: string;
  title: string;
  metadata?: PlotMetadata;
  onClose: () => void;
}

function sourceLabel(sourceType: string): string {
  switch (sourceType) {
    case "pipeline":
    case "plot_archive":
      return "Pipeline";
    case "notebook":
      return "Notebook";
    case "cellxgene":
      return "CellXGene";
    case "qc_dashboard":
      return "QC Dashboard";
    case "upload":
      return "Upload";
    default:
      return sourceType;
  }
}

function MetadataRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <span className="text-gray-400 text-xs w-24 shrink-0">{label}</span>
      <span className="text-gray-700 text-xs">{value}</span>
    </div>
  );
}

export function PlotModal({ url, title, metadata, onClose }: PlotModalProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const hasMetadata =
    metadata &&
    (metadata.experimentName ||
      metadata.projectName ||
      metadata.pipelineRunName ||
      metadata.notebookSessionType ||
      metadata.sourceType ||
      metadata.indexedAt ||
      (metadata.tags && metadata.tags.length > 0));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-lg shadow-xl max-w-[90vw] max-h-[90vh] overflow-auto mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between p-4 border-b bg-white rounded-t-lg">
          <h3 className="font-medium text-sm">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none px-2"
          >
            &times;
          </button>
        </div>
        <div className="p-4">
          <img src={url} alt={title} className="max-w-full" />
        </div>
        {hasMetadata && (
          <div className="px-4 pb-4 pt-2 border-t space-y-1.5">
            <MetadataRow label="Project" value={metadata.projectName} />
            <MetadataRow
              label="Experiment"
              value={metadata.experimentName}
            />
            <MetadataRow
              label="Pipeline"
              value={
                metadata.pipelineRunName
                  ? `${metadata.pipelineRunName} (#${metadata.pipelineRunId})`
                  : undefined
              }
            />
            <MetadataRow
              label="Session"
              value={
                metadata.notebookSessionType
                  ? `${metadata.notebookSessionType} (#${metadata.notebookSessionId})`
                  : undefined
              }
            />
            <MetadataRow
              label="Source"
              value={
                metadata.sourceType
                  ? sourceLabel(metadata.sourceType)
                  : undefined
              }
            />
            <MetadataRow
              label="Indexed"
              value={
                metadata.indexedAt
                  ? new Date(metadata.indexedAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : undefined
              }
            />
            {metadata.tags && metadata.tags.length > 0 && (
              <div className="flex gap-2 items-start">
                <span className="text-gray-400 text-xs w-24 shrink-0">
                  Tags
                </span>
                <div className="flex flex-wrap gap-1">
                  {metadata.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[10px]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
