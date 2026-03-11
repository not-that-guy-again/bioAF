"use client";

import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";
import type { PlotArchiveResponse, PlotArchiveListResponse } from "@/lib/types";

export default function PlotArchivePage() {
  const [plots, setPlots] = useState<PlotArchiveResponse[]>([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<PlotArchiveResponse | null>(null);
  const pageSize = 24;

  const fetchPlots = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (query) params.set("query", query);
      const data = await api.get<PlotArchiveListResponse>(`/api/plots?${params}`);
      setPlots(data.plots);
      setTotal(data.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [page, query]);

  useEffect(() => {
    fetchPlots();
  }, [fetchPlots]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Plot Archive</h1>

          <div className="space-y-4">
            <input
              type="text"
              placeholder="Search plots..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />

            {loading ? (
              <p className="text-gray-400 text-sm">Loading...</p>
            ) : plots.length === 0 ? (
              <p className="text-gray-400 text-sm">No plots found.</p>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  {plots.map((plot) => (
                    <div
                      key={plot.id}
                      onClick={() => setPreview(plot)}
                      className="bg-white rounded-lg shadow overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
                    >
                      <div className="aspect-square bg-gray-100 flex items-center justify-center">
                        {plot.thumbnail_url ? (
                          <img
                            src={plot.thumbnail_url ?? undefined}
                            alt={plot.title ?? undefined}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-gray-400 text-xs">No preview</span>
                        )}
                      </div>
                      <div className="p-2">
                        <p className="text-xs font-medium truncate">{plot.title}</p>
                        {plot.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {plot.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[10px]"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>{total} plot{total !== 1 ? "s" : ""}</span>
                  <div className="space-x-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page * pageSize >= total}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}

            {preview && (
              <div
                className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                onClick={() => setPreview(null)}
              >
                <div
                  className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 p-6"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold">{preview.title}</h3>
                      {preview.tags.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {preview.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => setPreview(null)}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      &times;
                    </button>
                  </div>
                  <div className="bg-gray-100 rounded-lg flex items-center justify-center min-h-[400px]">
                    {preview.file ? (
                      <img
                        src={preview.file.gcs_uri}
                        alt={preview.title ?? undefined}
                        className="max-w-full max-h-[600px] object-contain"
                      />
                    ) : (
                      <span className="text-gray-400">No image available</span>
                    )}
                  </div>
                  <div className="mt-3 text-xs text-gray-400">
                    {preview.experiment_id && <span>Experiment #{preview.experiment_id}</span>}
                    {preview.pipeline_run_id && <span> | Run #{preview.pipeline_run_id}</span>}
                    {preview.indexed_at && (
                      <span> | Indexed {new Date(preview.indexed_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
