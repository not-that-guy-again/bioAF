"use client";

import { useState, useCallback, useRef } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";
import type { FileResponse } from "@/lib/types";

interface UploadState {
  files: File[];
  experimentId: string;
  uploading: boolean;
  progress: Record<string, number>;
  errors: string[];
  successes: string[];
}

export default function DataUploadPage() {
  const [state, setState] = useState<UploadState>({
    files: [],
    experimentId: "",
    uploading: false,
    progress: {},
    errors: [],
    successes: [],
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (f) =>
        f.name.endsWith(".fastq") ||
        f.name.endsWith(".fastq.gz") ||
        f.name.endsWith(".fq") ||
        f.name.endsWith(".fq.gz") ||
        f.name.endsWith(".h5ad") ||
        f.name.endsWith(".csv") ||
        f.name.endsWith(".tsv")
    );
    setState((prev) => ({ ...prev, files: [...prev.files, ...droppedFiles] }));
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setState((prev) => ({
        ...prev,
        files: [...prev.files, ...Array.from(e.target.files!)],
      }));
    }
  };

  const removeFile = (index: number) => {
    setState((prev) => ({
      ...prev,
      files: prev.files.filter((_, i) => i !== index),
    }));
  };

  const uploadFiles = async () => {
    setState((prev) => ({ ...prev, uploading: true, errors: [], successes: [] }));

    for (const file of state.files) {
      try {
        setState((prev) => ({
          ...prev,
          progress: { ...prev.progress, [file.name]: 0 },
        }));

        const params = new URLSearchParams();
        if (state.experimentId) params.set("experiment_id", state.experimentId);
        const path = `/api/files/upload${params.toString() ? `?${params}` : ""}`;

        await api.upload<FileResponse>(path, file);

        setState((prev) => ({
          ...prev,
          progress: { ...prev.progress, [file.name]: 100 },
          successes: [...prev.successes, file.name],
        }));
      } catch (err) {
        setState((prev) => ({
          ...prev,
          errors: [...prev.errors, `${file.name}: ${err instanceof Error ? err.message : "Upload failed"}`],
        }));
      }
    }

    setState((prev) => ({ ...prev, uploading: false, files: [] }));
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Data Upload</h1>

          <div className="space-y-6">
            {/* Drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer hover:border-blue-400 transition-colors"
            >
              <p className="text-gray-500 mb-2">
                Drag & drop FASTQ, h5ad, CSV, or TSV files here
              </p>
              <p className="text-sm text-gray-400">or click to browse</p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".fastq,.fastq.gz,.fq,.fq.gz,.h5ad,.csv,.tsv"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            {/* Experiment linkage */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Link to Experiment (optional)
              </label>
              <input
                type="text"
                placeholder="Experiment ID"
                value={state.experimentId}
                onChange={(e) =>
                  setState((prev) => ({ ...prev, experimentId: e.target.value }))
                }
                className="w-48 px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>

            {/* File list */}
            {state.files.length > 0 && (
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-medium mb-3">
                  Selected Files ({state.files.length})
                </h3>
                <ul className="space-y-2">
                  {state.files.map((file, idx) => (
                    <li
                      key={`${file.name}-${idx}`}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="truncate flex-1">{file.name}</span>
                      <span className="text-gray-400 mx-4">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                      {state.progress[file.name] !== undefined && (
                        <div className="w-24 bg-gray-200 rounded-full h-2 mx-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all"
                            style={{ width: `${state.progress[file.name]}%` }}
                          />
                        </div>
                      )}
                      {!state.uploading && (
                        <button
                          onClick={() => removeFile(idx)}
                          className="text-red-400 hover:text-red-600 ml-2"
                        >
                          Remove
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={uploadFiles}
                  disabled={state.uploading}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {state.uploading ? "Uploading..." : "Upload All"}
                </button>
              </div>
            )}

            {/* Status messages */}
            {state.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                {state.errors.map((err, i) => (
                  <p key={i} className="text-sm text-red-700">
                    {err}
                  </p>
                ))}
              </div>
            )}
            {state.successes.length > 0 && (
              <div className="bg-green-50 border border-green-200 rounded-md p-3">
                {state.successes.map((s, i) => (
                  <p key={i} className="text-sm text-green-700">
                    Uploaded: {s}
                  </p>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
