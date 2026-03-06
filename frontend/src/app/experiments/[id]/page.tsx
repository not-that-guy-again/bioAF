"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ExperimentStatusBadge } from "@/components/experiments/ExperimentStatusBadge";
import { SampleQCBadge } from "@/components/experiments/SampleQCBadge";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type {
  ExperimentDetail,
  Sample,
  Batch,
  AuditLogResponse,
  AuditLogEntry,
  SampleCreateRequest,
  BatchCreateRequest,
  ExperimentStatus,
  QCStatus,
  NotebookSession,
  SessionListResponse,
} from "@/lib/types";

type Tab = "overview" | "samples" | "batches" | "analysis" | "pipelines" | "results" | "audit";

export default function ExperimentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [experiment, setExperiment] = useState<ExperimentDetail | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  const [notebookSessions, setNotebookSessions] = useState<NotebookSession[]>([]);

  const [showSampleForm, setShowSampleForm] = useState(false);
  const [showBatchForm, setShowBatchForm] = useState(false);
  const [sampleForm, setSampleForm] = useState<SampleCreateRequest>({});
  const [batchForm, setBatchForm] = useState<BatchCreateRequest>({ name: "" });

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadExperiment();
  }, [id, router]);

  useEffect(() => {
    if (activeTab === "samples") loadSamples();
    if (activeTab === "batches") loadBatches();
    if (activeTab === "analysis") loadNotebookSessions();
    if (activeTab === "audit") loadAudit();
  }, [activeTab, id]);

  async function loadExperiment() {
    try {
      const data = await api.get<ExperimentDetail>(`/api/experiments/${id}`);
      setExperiment(data);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  }

  async function loadSamples() {
    try {
      const data = await api.get<Sample[]>(`/api/experiments/${id}/samples`);
      setSamples(data);
    } catch {}
  }

  async function loadBatches() {
    try {
      const data = await api.get<Batch[]>(`/api/experiments/${id}/batches`);
      setBatches(data);
    } catch {}
  }

  async function loadAudit(page = 1) {
    try {
      const data = await api.get<AuditLogResponse>(`/api/experiments/${id}/audit?page=${page}`);
      setAuditEntries(data.entries);
      setAuditTotal(data.total);
    } catch {}
  }

  async function loadNotebookSessions() {
    try {
      const data = await api.get<SessionListResponse>("/api/notebooks/sessions");
      setNotebookSessions(data.sessions.filter(s => s.experiment?.id === Number(id)));
    } catch {}
  }

  async function handleLaunchNotebook(sessionType: "jupyter" | "rstudio") {
    try {
      await api.post("/api/notebooks/sessions", {
        session_type: sessionType,
        resource_profile: "small",
        experiment_id: Number(id),
      });
      loadNotebookSessions();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to launch session");
    }
  }

  async function handleAddSample() {
    try {
      await api.post(`/api/experiments/${id}/samples`, sampleForm);
      setSampleForm({});
      setShowSampleForm(false);
      loadSamples();
      loadExperiment();
    } catch {}
  }

  async function handleAddBatch() {
    try {
      await api.post(`/api/experiments/${id}/batches`, batchForm);
      setBatchForm({ name: "" });
      setShowBatchForm(false);
      loadBatches();
      loadExperiment();
    } catch {}
  }

  async function handleUpdateQC(sampleId: number, qcStatus: string) {
    try {
      await api.patch(`/api/samples/${sampleId}/qc`, { qc_status: qcStatus });
      loadSamples();
    } catch {}
  }

  async function handleCsvUpload(file: File) {
    try {
      await api.upload(`/api/experiments/${id}/samples/upload`, file);
      loadSamples();
      loadExperiment();
    } catch {}
  }

  async function handleStatusUpdate(newStatus: string) {
    try {
      await api.patch(`/api/experiments/${id}/status`, { status: newStatus });
      loadExperiment();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <p className="text-gray-500">Experiment not found</p>
          </main>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "samples", label: `Samples (${experiment.sample_count})` },
    { key: "batches", label: `Batches (${experiment.batch_count})` },
    { key: "analysis", label: "Analysis" },
    { key: "pipelines", label: "Pipeline Runs" },
    { key: "results", label: "Results" },
    { key: "audit", label: "Audit Trail" },
  ];

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-4 mb-6">
            <button onClick={() => router.push("/experiments")} className="text-gray-500 hover:text-gray-700">
              ← Back
            </button>
            <h1 className="text-2xl font-bold">{experiment.name}</h1>
            <ExperimentStatusBadge status={experiment.status} />
          </div>

          <div className="border-b border-gray-200 mb-6">
            <nav className="flex -mb-px space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`py-2 px-1 border-b-2 text-sm font-medium ${
                    activeTab === tab.key
                      ? "border-bioaf-500 text-bioaf-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Experiment Details</h2>
                <dl className="space-y-3">
                  <div><dt className="text-sm text-gray-500">Project</dt><dd className="text-sm">{experiment.project?.name || "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Owner</dt><dd className="text-sm">{experiment.owner?.name || experiment.owner?.email || "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Hypothesis</dt><dd className="text-sm">{experiment.hypothesis || "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Description</dt><dd className="text-sm">{experiment.description || "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Start Date</dt><dd className="text-sm">{experiment.start_date || "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Expected Samples</dt><dd className="text-sm">{experiment.expected_sample_count ?? "—"}</dd></div>
                  <div><dt className="text-sm text-gray-500">Actual Samples</dt><dd className="text-sm">{experiment.sample_count}</dd></div>
                  <div><dt className="text-sm text-gray-500">Created</dt><dd className="text-sm">{new Date(experiment.created_at).toLocaleString()}</dd></div>
                </dl>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Status</h2>
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <ExperimentStatusBadge status={experiment.status} />
                    <select
                      onChange={(e) => { if (e.target.value) handleStatusUpdate(e.target.value); e.target.value = ""; }}
                      className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                      defaultValue=""
                    >
                      <option value="" disabled>Advance status...</option>
                      {(["registered", "library_prep", "sequencing", "fastq_uploaded", "processing", "analysis", "complete"] as ExperimentStatus[])
                        .filter((s) => s !== experiment.status)
                        .map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                    </select>
                  </div>
                </div>

                {experiment.custom_fields.length > 0 && (
                  <>
                    <h3 className="text-md font-semibold mt-6 mb-3">Custom Fields</h3>
                    <dl className="space-y-2">
                      {experiment.custom_fields.map((cf) => (
                        <div key={cf.id}>
                          <dt className="text-sm text-gray-500">{cf.field_name}</dt>
                          <dd className="text-sm">{cf.field_value || "—"}</dd>
                        </div>
                      ))}
                    </dl>
                  </>
                )}
              </div>
            </div>
          )}

          {activeTab === "samples" && (
            <div>
              <div className="flex items-center gap-4 mb-4">
                <button
                  onClick={() => setShowSampleForm(!showSampleForm)}
                  className="bg-bioaf-600 text-white px-4 py-2 rounded-md text-sm hover:bg-bioaf-700"
                >
                  Add Sample
                </button>
                <label className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm cursor-pointer hover:bg-gray-50">
                  Upload CSV
                  <input
                    type="file"
                    accept=".csv,.tsv,.txt"
                    className="hidden"
                    onChange={(e) => { if (e.target.files?.[0]) handleCsvUpload(e.target.files[0]); }}
                  />
                </label>
              </div>

              {showSampleForm && (
                <div className="bg-white rounded-lg shadow p-4 mb-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <input placeholder="External ID" value={sampleForm.sample_id_external ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, sample_id_external: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Organism" value={sampleForm.organism ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, organism: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Tissue Type" value={sampleForm.tissue_type ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, tissue_type: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Donor/Source" value={sampleForm.donor_source ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, donor_source: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Treatment" value={sampleForm.treatment_condition ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, treatment_condition: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Chemistry Version" value={sampleForm.chemistry_version ?? ""} onChange={(e) => setSampleForm({ ...sampleForm, chemistry_version: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={handleAddSample} className="bg-bioaf-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                    <button onClick={() => setShowSampleForm(false)} className="border px-4 py-1.5 rounded text-sm">Cancel</button>
                  </div>
                </div>
              )}

              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">External ID</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Organism</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tissue</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Batch</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">QC</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {samples.map((s) => (
                      <tr key={s.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm">{s.sample_id_external || "—"}</td>
                        <td className="px-4 py-3 text-sm">{s.organism || "—"}</td>
                        <td className="px-4 py-3 text-sm">{s.tissue_type || "—"}</td>
                        <td className="px-4 py-3 text-sm">{s.batch?.name || "—"}</td>
                        <td className="px-4 py-3">
                          <select
                            value={s.qc_status ?? ""}
                            onChange={(e) => { if (e.target.value) handleUpdateQC(s.id, e.target.value); }}
                            className="text-xs border rounded px-2 py-1"
                          >
                            <option value="">—</option>
                            <option value="pass">Pass</option>
                            <option value="warning">Warning</option>
                            <option value="fail">Fail</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">{s.status.replace(/_/g, " ")}</td>
                      </tr>
                    ))}
                    {samples.length === 0 && (
                      <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No samples yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "batches" && (
            <div>
              <button
                onClick={() => setShowBatchForm(!showBatchForm)}
                className="bg-bioaf-600 text-white px-4 py-2 rounded-md text-sm hover:bg-bioaf-700 mb-4"
              >
                Create Batch
              </button>

              {showBatchForm && (
                <div className="bg-white rounded-lg shadow p-4 mb-4">
                  <div className="grid grid-cols-2 gap-3">
                    <input placeholder="Batch Name *" value={batchForm.name} onChange={(e) => setBatchForm({ ...batchForm, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
                    <input type="date" placeholder="Prep Date" value={batchForm.prep_date ?? ""} onChange={(e) => setBatchForm({ ...batchForm, prep_date: e.target.value || null })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Sequencer Run ID" value={batchForm.sequencer_run_id ?? ""} onChange={(e) => setBatchForm({ ...batchForm, sequencer_run_id: e.target.value || null })} className="border rounded px-3 py-2 text-sm" />
                    <input placeholder="Notes" value={batchForm.notes ?? ""} onChange={(e) => setBatchForm({ ...batchForm, notes: e.target.value || null })} className="border rounded px-3 py-2 text-sm" />
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={handleAddBatch} className="bg-bioaf-600 text-white px-4 py-1.5 rounded text-sm">Save</button>
                    <button onClick={() => setShowBatchForm(false)} className="border px-4 py-1.5 rounded text-sm">Cancel</button>
                  </div>
                </div>
              )}

              <div className="grid gap-4">
                {batches.map((b) => (
                  <div key={b.id} className="bg-white rounded-lg shadow p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold">{b.name}</h3>
                        <p className="text-sm text-gray-500">{b.sample_count} samples</p>
                      </div>
                      <div className="text-sm text-gray-500">
                        {b.prep_date && <span>Prep: {b.prep_date}</span>}
                        {b.sequencer_run_id && <span className="ml-4">Run: {b.sequencer_run_id}</span>}
                      </div>
                    </div>
                    {b.notes && <p className="text-sm text-gray-500 mt-2">{b.notes}</p>}
                  </div>
                ))}
                {batches.length === 0 && (
                  <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">No batches yet</div>
                )}
              </div>
            </div>
          )}

          {activeTab === "analysis" && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Launch Notebook</h2>
                <p className="text-sm text-gray-500 mb-4">
                  Start a Jupyter or RStudio session pre-linked to this experiment.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleLaunchNotebook("jupyter")}
                    className="bg-bioaf-600 text-white px-6 py-2 rounded-md text-sm hover:bg-bioaf-700"
                  >
                    Launch Jupyter
                  </button>
                  <button
                    onClick={() => handleLaunchNotebook("rstudio")}
                    className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm hover:bg-blue-700"
                  >
                    Launch RStudio
                  </button>
                </div>
              </div>

              {notebookSessions.length > 0 && (
                <div className="bg-white rounded-lg shadow">
                  <div className="p-6 border-b">
                    <h2 className="text-lg font-semibold">Linked Sessions</h2>
                  </div>
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profile</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {notebookSessions.map((s) => (
                        <tr key={s.id}>
                          <td className="px-4 py-3 text-sm capitalize">{s.session_type}</td>
                          <td className="px-4 py-3 text-sm">{s.status}</td>
                          <td className="px-4 py-3 text-sm capitalize">{s.resource_profile}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{new Date(s.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === "pipelines" && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <h2 className="text-lg font-semibold text-gray-400 mb-2">Pipeline Runs</h2>
              <p className="text-gray-400">Pipeline runs will appear here when pipelines are configured. Coming in Phase 4.</p>
            </div>
          )}

          {activeTab === "results" && (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <h2 className="text-lg font-semibold text-gray-400 mb-2">Results</h2>
              <p className="text-gray-400">Results and visualizations will appear here. Coming in Phase 5.</p>
            </div>
          )}

          {activeTab === "audit" && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Audit Trail ({auditTotal} entries)</h2>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      const blob = await api.post<Blob>(`/api/experiments/${id}/audit/export`, { format: "csv" });
                    }}
                    className="border px-3 py-1.5 rounded text-sm hover:bg-gray-50"
                  >
                    Export CSV
                  </button>
                  <button
                    onClick={async () => {
                      const blob = await api.post<Blob>(`/api/experiments/${id}/audit/export`, { format: "json" });
                    }}
                    className="border px-3 py-1.5 rounded text-sm hover:bg-gray-50"
                  >
                    Export JSON
                  </button>
                </div>
              </div>
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {auditEntries.map((e) => (
                      <tr key={e.id}>
                        <td className="px-4 py-3 text-sm text-gray-500">{new Date(e.timestamp).toLocaleString()}</td>
                        <td className="px-4 py-3 text-sm">{e.entity_type} #{e.entity_id}</td>
                        <td className="px-4 py-3 text-sm">{e.action}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {e.details ? (
                            <details>
                              <summary className="cursor-pointer">View</summary>
                              <pre className="text-xs mt-1 bg-gray-50 p-2 rounded overflow-auto max-w-md">
                                {JSON.stringify(e.details, null, 2)}
                              </pre>
                            </details>
                          ) : "—"}
                        </td>
                      </tr>
                    ))}
                    {auditEntries.length === 0 && (
                      <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No audit entries</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
