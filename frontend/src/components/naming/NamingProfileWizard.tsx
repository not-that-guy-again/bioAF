"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ProjectOption {
  id: number;
  name: string;
  code: string | null;
}

interface ExperimentOption {
  id: number;
  name: string;
  code: string | null;
}

interface SegmentAssignment {
  value: string;
  field: string;
  mappedEntityId?: number;
}

const FIELD_OPTIONS = [
  { value: "project_code", label: "Project Code" },
  { value: "experiment_code", label: "Experiment Code" },
  { value: "sample_id", label: "Sample ID" },
  { value: "data_type", label: "Data Type" },
  { value: "date", label: "Date" },
  { value: "version", label: "Version" },
  { value: "organism", label: "Organism" },
  { value: "researcher_initials", label: "Researcher Initials" },
  { value: "analysis_type", label: "Analysis Type" },
  { value: "batch_id", label: "Batch ID" },
  { value: "ignore", label: "Ignore" },
];

type Step = "filename" | "assign" | "map" | "verify" | "save";

interface Props {
  onSave: () => void;
  onCancel: () => void;
}

export function NamingProfileWizard({ onSave, onCancel }: Props) {
  const [step, setStep] = useState<Step>("filename");
  const [filename, setFilename] = useState("");
  const [delimiter, setDelimiter] = useState("_");
  const [segments, setSegments] = useState<string[]>([]);
  const [assignments, setAssignments] = useState<SegmentAssignment[]>([]);
  const [profileName, setProfileName] = useState("");
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [experiments, setExperiments] = useState<ExperimentOption[]>([]);
  const [verifyFilename, setVerifyFilename] = useState("");
  const [verifyResult, setVerifyResult] = useState<Record<string, string> | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<ProjectOption[]>("/api/projects?page_size=100").then((data) => {
      // API returns {projects: [...], total: ...}
      const items = Array.isArray(data) ? data : (data as unknown as { projects: ProjectOption[] }).projects ?? [];
      setProjects(items);
    }).catch(() => {});
    api.get<ExperimentOption[]>("/api/experiments?page_size=100").then((data) => {
      const items = Array.isArray(data) ? data : (data as unknown as { experiments: ExperimentOption[] }).experiments ?? [];
      setExperiments(items);
    }).catch(() => {});
  }, []);

  function splitFilename() {
    let name = filename.trim();
    // Strip extensions (.fastq.gz, .bam, etc.)
    name = name.replace(/\.(fastq|fq)(\.gz|\.bz2)?$/i, "");
    name = name.replace(/\.(bam|sam|h5ad|h5|csv|tsv|txt|bed|vcf|gtf|gff)(\.gz)?$/i, "");
    const parts = name.split(delimiter);
    setSegments(parts);
    setAssignments(parts.map((value) => ({ value, field: "ignore" })));
    // Auto-detect common patterns
    const autoAssigned = parts.map((value, i) => {
      const lower = value.toLowerCase();
      if (lower.startsWith("s") && /^s\d+$/i.test(lower)) return { value, field: "sample_id" };
      if (lower.startsWith("l") && /^l\d+$/i.test(lower)) return { value, field: "ignore" };
      if (lower.startsWith("r") && /^r[12]$/i.test(lower)) return { value, field: "data_type" };
      if (lower.startsWith("i") && /^i[12]$/i.test(lower)) return { value, field: "data_type" };
      if (/^\d{4}-?\d{2}-?\d{2}$/.test(value)) return { value, field: "date" };
      if (/^v\d+$/i.test(value)) return { value, field: "version" };
      if (i === 0) return { value, field: "project_code" };
      return { value, field: "ignore" };
    });
    setAssignments(autoAssigned);
    setStep("assign");
  }

  function updateAssignment(idx: number, field: string) {
    setAssignments((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, field } : a))
    );
  }

  function updateMapping(idx: number, entityId: number) {
    setAssignments((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, mappedEntityId: entityId } : a))
    );
  }

  const needsMapping = assignments.some(
    (a) => a.field === "project_code" || a.field === "experiment_code"
  );

  function handleVerify() {
    if (!verifyFilename.trim()) return;
    let name = verifyFilename.trim();
    name = name.replace(/\.(fastq|fq)(\.gz|\.bz2)?$/i, "");
    name = name.replace(/\.(bam|sam|h5ad|h5|csv|tsv|txt|bed|vcf|gtf|gff)(\.gz)?$/i, "");
    const parts = name.split(delimiter);
    const result: Record<string, string> = {};
    parts.forEach((val, i) => {
      if (i < assignments.length && assignments[i].field !== "ignore") {
        const field = assignments[i].field;
        result[field] = val;
        // Show mapped entity name
        if (field === "project_code" && assignments[i].mappedEntityId) {
          const proj = projects.find((p) => p.id === assignments[i].mappedEntityId);
          if (proj) result[`${field}_resolved`] = proj.name;
        }
        if (field === "experiment_code" && assignments[i].mappedEntityId) {
          const exp = experiments.find((e) => e.id === assignments[i].mappedEntityId);
          if (exp) result[`${field}_resolved`] = exp.name;
        }
      }
    });
    setVerifyResult(result);
  }

  async function handleSave() {
    setError("");
    setSaving(true);

    const segmentDefs = assignments.map((a, i) => ({
      position: i,
      field: a.field,
      required: a.field !== "ignore",
    }));

    const projectMappings: Record<string, string> = {};
    const experimentMappings: Record<string, string> = {};
    for (const a of assignments) {
      if (a.field === "project_code" && a.mappedEntityId) {
        projectMappings[a.value] = String(a.mappedEntityId);
      }
      if (a.field === "experiment_code" && a.mappedEntityId) {
        experimentMappings[a.value] = String(a.mappedEntityId);
      }
    }

    try {
      await api.post("/api/naming-profiles", {
        name: profileName || `Profile for ${filename}`,
        delimiter,
        strip_extension: true,
        segments: segmentDefs,
        project_code_mappings: projectMappings,
        experiment_code_mappings: experimentMappings,
      });
      onSave();
    } catch {
      setError("Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white border rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Create Naming Profile</h2>

      {/* Step 1: Enter filename and delimiter */}
      {step === "filename" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Paste a real filename from your data. The wizard will split it into segments and
            help you assign each one.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sample filename</label>
            <input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="e.g. pbmc01_s001_l001_r2_i2.fastq.gz"
              className="w-full border rounded-lg px-3 py-2 font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Delimiter</label>
            <div className="flex gap-3">
              {[
                { value: "_", label: "Underscore (_)" },
                { value: "-", label: "Hyphen (-)" },
                { value: ".", label: "Dot (.)" },
              ].map((d) => (
                <label key={d.value} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input
                    type="radio"
                    name="delimiter"
                    value={d.value}
                    checked={delimiter === d.value}
                    onChange={() => setDelimiter(d.value)}
                  />
                  {d.label}
                </label>
              ))}
            </div>
          </div>
          {filename && (
            <div className="bg-gray-50 rounded-md p-3">
              <p className="text-xs text-gray-500 mb-1">Preview</p>
              <div className="flex flex-wrap gap-1">
                {filename.replace(/\.(fastq|fq)(\.gz|\.bz2)?$/i, "")
                  .replace(/\.(bam|sam|h5ad|h5|csv|tsv|txt|bed|vcf|gtf|gff)(\.gz)?$/i, "")
                  .split(delimiter)
                  .map((part, i) => (
                    <span
                      key={i}
                      className="bg-white border rounded px-2 py-1 font-mono text-sm"
                    >
                      {part}
                    </span>
                  ))}
              </div>
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={splitFilename}
              disabled={!filename.trim()}
              className="px-4 py-2 bg-bioaf-600 text-white rounded-lg hover:bg-bioaf-700 disabled:opacity-50"
            >
              Next
            </button>
            <button onClick={onCancel} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Assign segments */}
      {step === "assign" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Assign a role to each segment of the filename. The system auto-detected some
            common patterns. Adjust as needed.
          </p>
          <div className="space-y-2">
            {segments.map((seg, i) => (
              <div key={i} className="flex items-center gap-3 bg-gray-50 rounded-md p-3">
                <span className="font-mono text-sm font-medium text-gray-800 min-w-[120px] bg-white border rounded px-2 py-1">
                  {seg}
                </span>
                <span className="text-gray-400">&rarr;</span>
                <select
                  value={assignments[i]?.field || "ignore"}
                  onChange={(e) => updateAssignment(i, e.target.value)}
                  className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1.5"
                >
                  {FIELD_OPTIONS.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setStep(needsMapping ? "map" : "verify")}
              className="px-4 py-2 bg-bioaf-600 text-white rounded-lg hover:bg-bioaf-700"
            >
              Next
            </button>
            <button onClick={() => setStep("filename")} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
              Back
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Map codes to entities */}
      {step === "map" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Map the extracted codes to your existing projects and experiments. This tells the
            system which project/experiment a file belongs to based on its filename.
          </p>
          <div className="space-y-3">
            {assignments.map((a, i) => {
              if (a.field === "project_code") {
                return (
                  <div key={i} className="flex items-center gap-3 bg-gray-50 rounded-md p-3">
                    <span className="text-sm text-gray-600 min-w-[100px]">Project code</span>
                    <span className="font-mono text-sm font-medium bg-white border rounded px-2 py-1">
                      {a.value}
                    </span>
                    <span className="text-gray-400">&rarr;</span>
                    <select
                      value={a.mappedEntityId || ""}
                      onChange={(e) => updateMapping(i, parseInt(e.target.value, 10))}
                      className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1.5"
                    >
                      <option value="">Select a project...</option>
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} {p.code ? `(${p.code})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              }
              if (a.field === "experiment_code") {
                return (
                  <div key={i} className="flex items-center gap-3 bg-gray-50 rounded-md p-3">
                    <span className="text-sm text-gray-600 min-w-[100px]">Experiment code</span>
                    <span className="font-mono text-sm font-medium bg-white border rounded px-2 py-1">
                      {a.value}
                    </span>
                    <span className="text-gray-400">&rarr;</span>
                    <select
                      value={a.mappedEntityId || ""}
                      onChange={(e) => updateMapping(i, parseInt(e.target.value, 10))}
                      className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1.5"
                    >
                      <option value="">Select an experiment...</option>
                      {experiments.map((exp) => (
                        <option key={exp.id} value={exp.id}>
                          {exp.name} {exp.code ? `(${exp.code})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              }
              return null;
            })}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setStep("verify")}
              className="px-4 py-2 bg-bioaf-600 text-white rounded-lg hover:bg-bioaf-700"
            >
              Next
            </button>
            <button onClick={() => setStep("assign")} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
              Back
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Verify with another file */}
      {step === "verify" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Test the profile against another filename to make sure it parses correctly.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Profile name</label>
            <input
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              placeholder={`Profile for ${filename}`}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div className="bg-gray-50 rounded-md p-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Profile summary</p>
            <div className="text-xs text-gray-600 space-y-1">
              <p>Delimiter: <span className="font-mono font-medium">{delimiter === "_" ? "underscore" : delimiter === "-" ? "hyphen" : "dot"}</span></p>
              <p>Segments: {assignments.filter((a) => a.field !== "ignore").map((a) => a.field).join(", ")}</p>
              {assignments.filter((a) => a.mappedEntityId).map((a, i) => (
                <p key={i}>
                  {a.field === "project_code" ? "Project" : "Experiment"} mapping:{" "}
                  <span className="font-mono">{a.value}</span> &rarr;{" "}
                  {a.field === "project_code"
                    ? projects.find((p) => p.id === a.mappedEntityId)?.name
                    : experiments.find((e) => e.id === a.mappedEntityId)?.name}
                </p>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Verify with another filename (optional)
            </label>
            <div className="flex gap-2">
              <input
                value={verifyFilename}
                onChange={(e) => { setVerifyFilename(e.target.value); setVerifyResult(null); }}
                placeholder="Paste another filename to test..."
                className="flex-1 border rounded-lg px-3 py-2 font-mono text-sm"
              />
              <button
                onClick={handleVerify}
                disabled={!verifyFilename.trim()}
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Test
              </button>
            </div>
          </div>

          {verifyResult && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <p className="text-sm font-medium text-green-800 mb-2">Parsed result</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {Object.entries(verifyResult).filter(([k]) => !k.endsWith("_resolved")).map(([key, val]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-gray-600">{key}:</span>
                    <span className="font-mono font-medium">{val}</span>
                    {verifyResult[`${key}_resolved`] && (
                      <span className="text-green-700">({verifyResult[`${key}_resolved`]})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-bioaf-600 text-white rounded-lg hover:bg-bioaf-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Profile"}
            </button>
            <button
              onClick={() => setStep(needsMapping ? "map" : "assign")}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
