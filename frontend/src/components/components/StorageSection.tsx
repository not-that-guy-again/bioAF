"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface BucketInfo {
  name: string;
  purpose: string;
  is_ingest: boolean;
  size_gb: number;
  object_count: number;
}

interface StorageBucketsResponse {
  org_slug: string;
  buckets: BucketInfo[];
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button
      onClick={handleCopy}
      aria-label="Copy"
      className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50 text-gray-600"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function IngestGuidancePanel({ bucket }: { bucket: BucketInfo }) {
  const gsUri = `gs://${bucket.name}/`;
  const gsutilCmd = `gsutil cp your_file.fastq.gz ${gsUri}`;

  return (
    <div className="mt-3 p-3 bg-teal-50 border border-teal-200 rounded text-sm space-y-2">
      <p className="text-teal-800 font-medium text-xs uppercase tracking-wide">Upload Files</p>
      <div className="flex items-center gap-2">
        <code className="flex-1 text-xs bg-white border border-teal-200 rounded px-2 py-1 font-mono text-gray-800 truncate">
          {gsutilCmd}
        </code>
        <CopyButton text={gsUri} />
      </div>
      <div className="flex gap-4 text-xs text-teal-700">
        <Link href="/settings/naming-profiles" className="underline hover:text-teal-900">
          Configure naming profiles
        </Link>
        <Link href="/data/browser" className="underline hover:text-teal-900">
          View ingested files
        </Link>
      </div>
    </div>
  );
}

function BucketCard({ bucket }: { bucket: BucketInfo }) {
  const isIngest = bucket.is_ingest;
  const cardClass = isIngest
    ? "bg-white rounded-lg border-2 border-teal-400 p-4 shadow-sm"
    : "bg-white rounded-lg border border-gray-200 p-4 shadow-sm";

  return (
    <div data-testid={`bucket-card-${bucket.name}`} className={cardClass}>
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-mono text-sm font-semibold text-gray-800">{bucket.name}</h3>
        {isIngest && (
          <span className="text-xs bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full font-medium">
            Ingest
          </span>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-2">{bucket.purpose}</p>
      <div className="flex gap-4 text-xs text-gray-400">
        <span>{bucket.size_gb.toFixed(2)} GB</span>
        <span>{bucket.object_count} objects</span>
      </div>
      {isIngest && <IngestGuidancePanel bucket={bucket} />}
    </div>
  );
}

export function StorageSection() {
  const [data, setData] = useState<StorageBucketsResponse | null>(null);

  useEffect(() => {
    api
      .get<StorageBucketsResponse>("/api/v1/infrastructure/storage/buckets")
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.buckets.map((bucket) => (
          <BucketCard key={bucket.name} bucket={bucket} />
        ))}
      </div>
    </div>
  );
}
