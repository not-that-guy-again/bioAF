"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type {
  Experiment,
  ExperimentCreateRequest,
  ExperimentTemplate,
  ProjectListResponse,
  SampleCreateRequest,
} from "@/lib/types";

export default function NewExperimentPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<{ id: number; name: string }[]>([]);
  const [templates, setTemplates] = useState<ExperimentTemplate[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState<ExperimentCreateRequest>({
    name: "",
    project_id: null,
    template_id: null,
    hypothesis: null,
    description: null,
    start_date: new Date().toISOString().split("T")[0],
    expected_sample_count: null,
  });

  const [csvFile, setCsvFile] = useState<File | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    Promise.all([
      api.get<ProjectListResponse>("/api/projects"),
      api.get<ExperimentTemplate[]>("/api/templates"),
    ]).then(([projData, templateData]) => {
      setProjects(projData.projects.map((p) => ({ id: p.id, name: p.name })));
      setTemplates(templateData);
    }).catch(() => {});
  }, [router]);

  const selectedTemplate = templates.find((t) => t.id === form.template_id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Name is required");
      return;
    }
    setSubmitting(true);
    setError("");

    try {
      const experiment = await api.post<Experiment>("/api/experiments", form);

      if (csvFile) {
        await api.upload(`/api/experiments/${experiment.id}/samples/upload`, csvFile);
      }

      router.push(`/experiments/${experiment.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create experiment");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">New Experiment</h1>

          <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <h2 className="text-lg font-semibold">Basics</h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template (optional)</label>
                <select
                  value={form.template_id ?? ""}
                  onChange={(e) => setForm({ ...form, template_id: e.target.value ? Number(e.target.value) : null })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">No template</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
                <select
                  value={form.project_id ?? ""}
                  onChange={(e) => setForm({ ...form, project_id: e.target.value ? Number(e.target.value) : null })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">No project</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hypothesis</label>
                <textarea
                  value={form.hypothesis ?? ""}
                  onChange={(e) => setForm({ ...form, hypothesis: e.target.value || null })}
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={form.description ?? ""}
                  onChange={(e) => setForm({ ...form, description: e.target.value || null })}
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={form.start_date ?? ""}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value || null })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Expected Sample Count</label>
                  <input
                    type="number"
                    min={0}
                    value={form.expected_sample_count ?? ""}
                    onChange={(e) => setForm({ ...form, expected_sample_count: e.target.value ? Number(e.target.value) : null })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>

            {selectedTemplate?.custom_fields_schema_json && (
              <div className="bg-white rounded-lg shadow p-6 space-y-4">
                <h2 className="text-lg font-semibold">Custom Fields</h2>
                <p className="text-sm text-gray-500">
                  Fields defined by the &quot;{selectedTemplate.name}&quot; template.
                </p>
                {(selectedTemplate.custom_fields_schema_json as { fields?: Array<{ name: string; type: string; required?: boolean }> })?.fields?.map((field) => (
                  <div key={field.name}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {field.name} {field.required && "*"}
                    </label>
                    <input
                      type={field.type === "number" ? "number" : "text"}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <h2 className="text-lg font-semibold">Initial Samples (optional)</h2>
              <p className="text-sm text-gray-500">
                Upload a CSV/TSV file to add samples when the experiment is created.
              </p>
              <input
                type="file"
                accept=".csv,.tsv,.txt"
                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-bioaf-50 file:text-bioaf-700 hover:file:bg-bioaf-100"
              />
              {csvFile && (
                <p className="text-sm text-gray-600">
                  Selected: {csvFile.name} ({(csvFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            <div className="flex gap-4">
              <button
                type="submit"
                disabled={submitting}
                className="bg-bioaf-600 text-white px-6 py-2 rounded-md hover:bg-bioaf-700 disabled:opacity-50"
              >
                {submitting ? "Creating..." : "Create Experiment"}
              </button>
              <button
                type="button"
                onClick={() => router.back()}
                className="border border-gray-300 px-6 py-2 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </main>
      </div>
    </div>
  );
}
