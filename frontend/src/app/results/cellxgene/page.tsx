"use client";

import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { api } from "@/lib/api";
import type { CellxgenePublicationResponse } from "@/lib/types";

export default function CellxgenePage() {
  const [publications, setPublications] = useState<CellxgenePublicationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPublishForm, setShowPublishForm] = useState(false);
  const [publishForm, setPublishForm] = useState({ file_id: "", experiment_id: "", dataset_name: "" });

  const fetchPublications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<CellxgenePublicationResponse[]>("/api/cellxgene");
      setPublications(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPublications();
  }, [fetchPublications]);

  const handlePublish = async () => {
    try {
      await api.post("/api/cellxgene/publish", {
        file_id: parseInt(publishForm.file_id),
        experiment_id: publishForm.experiment_id ? parseInt(publishForm.experiment_id) : null,
        dataset_name: publishForm.dataset_name,
      });
      setShowPublishForm(false);
      setPublishForm({ file_id: "", experiment_id: "", dataset_name: "" });
      fetchPublications();
    } catch {
      // ignore
    }
  };

  const handleUnpublish = async (id: number) => {
    if (!confirm("Unpublish this dataset?")) return;
    try {
      await api.delete(`/api/cellxgene/${id}`);
      fetchPublications();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">cellxgene Explorer</h1>
            <button
              onClick={() => setShowPublishForm(!showPublishForm)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              Publish Dataset
            </button>
          </div>

          <p className="text-sm text-gray-500 mb-6">
            Publish h5ad datasets for interactive exploration with cellxgene.
          </p>

          {showPublishForm && (
            <div className="bg-white rounded-lg shadow p-4 space-y-3 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">File ID (h5ad)</label>
                <input
                  type="text"
                  value={publishForm.file_id}
                  onChange={(e) => setPublishForm((f) => ({ ...f, file_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dataset Name</label>
                <input
                  type="text"
                  value={publishForm.dataset_name}
                  onChange={(e) => setPublishForm((f) => ({ ...f, dataset_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Experiment ID (optional)</label>
                <input
                  type="text"
                  value={publishForm.experiment_id}
                  onChange={(e) => setPublishForm((f) => ({ ...f, experiment_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                />
              </div>
              <button
                onClick={handlePublish}
                disabled={!publishForm.file_id || !publishForm.dataset_name}
                className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
              >
                Publish
              </button>
            </div>
          )}

          {loading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : publications.length === 0 ? (
            <p className="text-gray-400 text-sm">No published datasets.</p>
          ) : (
            <div className="bg-white rounded-lg shadow divide-y divide-gray-200">
              {publications.map((pub) => (
                <div
                  key={pub.id}
                  className="p-4 flex items-center justify-between hover:bg-gray-50"
                >
                  <div>
                    <p className="font-medium text-sm">{pub.dataset_name}</p>
                    <p className="text-xs text-gray-400">
                      Status: {pub.status}
                      {pub.published_at && ` | Published ${new Date(pub.published_at).toLocaleDateString()}`}
                    </p>
                  </div>
                  <div className="flex gap-3 items-center">
                    {pub.stable_url && pub.status === "running" && (
                      <a
                        href={pub.stable_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 text-sm hover:underline"
                      >
                        Open
                      </a>
                    )}
                    <button
                      onClick={() => handleUnpublish(pub.id)}
                      className="text-red-500 text-sm hover:underline"
                    >
                      Unpublish
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
