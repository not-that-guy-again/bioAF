"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { isAuthenticated, getCurrentUser } from "@/lib/auth";
import { api } from "@/lib/api";

interface AccessLogEntry {
  id: number;
  user_id: number;
  resource_type: string;
  resource_id: string;
  action: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

interface NeverLoggedInUser {
  id: number;
  email: string;
  name: string | null;
  role: string;
  status: string;
  created_at: string | null;
}

export default function SettingsAccessLogsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<AccessLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [resourceType, setResourceType] = useState("");
  const [action, setAction] = useState("");
  const [neverLoggedIn, setNeverLoggedIn] = useState<NeverLoggedInUser[]>([]);
  const [neverLoggedInLoading, setNeverLoggedInLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    const user = getCurrentUser();
    if (user?.role !== "admin") { router.push("/"); return; }
  }, [router]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        let url = `/api/access-logs?page=${page}&page_size=50`;
        if (resourceType) url += `&resource_type=${resourceType}`;
        if (action) url += `&action=${action}`;
        const data = await api.get<{ logs: AccessLogEntry[]; total: number }>(url);
        setLogs(data.logs);
        setTotal(data.total);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [page, resourceType, action]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.get<{ users: NeverLoggedInUser[] }>("/api/access-logs/never-logged-in");
        setNeverLoggedIn(data.users);
      } catch {
        // ignore
      } finally {
        setNeverLoggedInLoading(false);
      }
    };
    load();
  }, []);

  const totalPages = Math.ceil(total / 50);

  function userLabel(entry: AccessLogEntry): string {
    const meta = entry.metadata_json;
    if (meta?.email && typeof meta.email === "string") return meta.email;
    return `User #${entry.user_id}`;
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Access Logs</h1>

          {/* Never-logged-in banner */}
          {!neverLoggedInLoading && neverLoggedIn.length > 0 && (
            <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h2 className="text-sm font-semibold text-amber-800 mb-2">
                Users who have never logged in ({neverLoggedIn.length})
              </h2>
              <div className="flex flex-wrap gap-2">
                {neverLoggedIn.map((u) => (
                  <span
                    key={u.id}
                    className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded"
                  >
                    {u.email}
                    <span className="text-amber-500">({u.role})</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 mb-4">
            <select
              value={resourceType}
              onChange={(e) => { setResourceType(e.target.value); setPage(1); }}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            >
              <option value="">All resource types</option>
              <option value="auth">Auth</option>
              <option value="file">File</option>
              <option value="notebook">Notebook</option>
              <option value="dataset">Dataset</option>
              <option value="cellxgene">CellxGene</option>
            </select>
            <select
              value={action}
              onChange={(e) => { setAction(e.target.value); setPage(1); }}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            >
              <option value="">All actions</option>
              <option value="login">Login</option>
              <option value="read">Read</option>
              <option value="download">Download</option>
              <option value="view">View</option>
              <option value="session">Session</option>
            </select>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-700">User</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-700">Resource</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-700">Resource ID</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-700">Action</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-700">Time</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
                ) : logs.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No access logs</td></tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2.5 text-gray-900">{userLabel(log)}</td>
                      <td className="px-4 py-2.5 text-gray-600">{log.resource_type}</td>
                      <td className="px-4 py-2.5 text-gray-600 font-mono text-xs">{log.resource_id}</td>
                      <td className="px-4 py-2.5">
                        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">{log.action}</span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{new Date(log.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Previous</button>
              <span className="px-3 py-1 text-sm text-gray-600">Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Next</button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
