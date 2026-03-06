"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api";
import type {
  PackageSearchResult,
  PackageSearchResponse,
  InstalledPackage,
  EnvironmentResponse,
  EnvironmentListResponse,
  EnvironmentDetailResponse,
} from "@/lib/types";

const SOURCE_OPTIONS = ["conda", "pip", "cran", "bioconductor"] as const;

export default function PackagesPage() {
  const router = useRouter();

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PackageSearchResult[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>(["conda", "pip"]);
  const [searching, setSearching] = useState(false);

  const [environments, setEnvironments] = useState<EnvironmentResponse[]>([]);
  const [selectedEnv, setSelectedEnv] = useState("");
  const [installedPackages, setInstalledPackages] = useState<InstalledPackage[]>([]);
  const [loadingPackages, setLoadingPackages] = useState(false);

  const [installTarget, setInstallTarget] = useState<PackageSearchResult | null>(null);
  const [installEnv, setInstallEnv] = useState("");
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/login"); return; }
    loadEnvironments();
  }, [router]);

  async function loadEnvironments() {
    try {
      const data = await api.get<EnvironmentListResponse>("/api/environments");
      setEnvironments(data.environments);
      if (data.environments.length > 0) {
        setSelectedEnv(data.environments[0].name);
        loadInstalledPackages(data.environments[0].name);
      }
    } catch {}
  }

  async function loadInstalledPackages(envName: string) {
    setLoadingPackages(true);
    try {
      const data = await api.get<EnvironmentDetailResponse>(`/api/environments/${envName}`);
      setInstalledPackages(data.packages);
    } catch {} finally { setLoadingPackages(false); }
  }

  const doSearch = useCallback(async (query: string) => {
    if (query.length < 2) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const sources = selectedSources.join(",");
      const data = await api.get<PackageSearchResponse>(
        `/api/packages/search?query=${encodeURIComponent(query)}&sources=${sources}&limit=20`
      );
      setSearchResults(data.results);
    } catch {} finally { setSearching(false); }
  }, [selectedSources]);

  useEffect(() => {
    const timer = setTimeout(() => doSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery, doSearch]);

  async function handleInstall() {
    if (!installTarget || !installEnv) return;
    setInstalling(true);
    try {
      await api.post("/api/packages/install", {
        environment: installEnv,
        package_name: installTarget.name,
        version: installTarget.version,
        source: installTarget.source,
        pinned: false,
      });
      setInstallTarget(null);
      if (installEnv === selectedEnv) loadInstalledPackages(selectedEnv);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Install failed");
    } finally { setInstalling(false); }
  }

  async function handleRemove(pkg: InstalledPackage) {
    if (!confirm(`Remove ${pkg.name} from ${selectedEnv}?`)) return;
    try {
      await api.post("/api/packages/remove", {
        environment: selectedEnv,
        package_name: pkg.name,
        source: pkg.source,
      });
      loadInstalledPackages(selectedEnv);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Remove failed");
    }
  }

  const sourceBadgeColor: Record<string, string> = {
    conda: "bg-green-100 text-green-700",
    pip: "bg-blue-100 text-blue-700",
    cran: "bg-purple-100 text-purple-700",
    bioconductor: "bg-orange-100 text-orange-700",
  };

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <h1 className="text-2xl font-bold mb-6">Package Management</h1>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Search Panel */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="font-semibold text-lg mb-4">Search Packages</h2>
              <input
                type="text"
                placeholder="Search for packages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm mb-3"
              />
              <div className="flex gap-2 mb-4">
                {SOURCE_OPTIONS.map((src) => (
                  <label key={src} className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      checked={selectedSources.includes(src)}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedSources([...selectedSources, src]);
                        else setSelectedSources(selectedSources.filter((s) => s !== src));
                      }}
                    />
                    {src}
                  </label>
                ))}
              </div>

              {searching && <div className="py-4 text-center"><LoadingSpinner size="sm" /></div>}

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {searchResults.map((pkg, i) => (
                  <div key={`${pkg.name}-${pkg.source}-${i}`} className="flex items-center justify-between p-3 border rounded-md">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{pkg.name}</span>
                        <span className={`px-1.5 py-0.5 text-xs rounded ${sourceBadgeColor[pkg.source] || "bg-gray-100"}`}>
                          {pkg.source}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{pkg.description || `v${pkg.version}`}</p>
                    </div>
                    <button
                      onClick={() => { setInstallTarget(pkg); setInstallEnv(selectedEnv); }}
                      className="bg-bioaf-600 text-white px-3 py-1 rounded text-xs hover:bg-bioaf-700"
                    >
                      Install
                    </button>
                  </div>
                ))}
                {searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
                  <p className="text-center text-gray-400 text-sm py-4">No packages found</p>
                )}
              </div>
            </div>

            {/* Installed Packages Panel */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-lg">Installed Packages</h2>
                <select
                  value={selectedEnv}
                  onChange={(e) => { setSelectedEnv(e.target.value); loadInstalledPackages(e.target.value); }}
                  className="border rounded px-2 py-1 text-sm"
                >
                  {environments.map((env) => (
                    <option key={env.name} value={env.name}>{env.name}</option>
                  ))}
                </select>
              </div>

              {loadingPackages ? (
                <div className="py-4 text-center"><LoadingSpinner size="sm" /></div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-500">
                        <th className="py-2">Package</th>
                        <th className="py-2">Version</th>
                        <th className="py-2">Source</th>
                        <th className="py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {installedPackages.map((pkg) => (
                        <tr key={`${pkg.name}-${pkg.source}`} className="border-b last:border-0">
                          <td className="py-2 flex items-center gap-1">
                            {pkg.name}
                            {pkg.pinned && <span title="Pinned" className="text-yellow-500">&#128274;</span>}
                          </td>
                          <td className="py-2 text-gray-500">{pkg.version || "latest"}</td>
                          <td className="py-2">
                            <span className={`px-1.5 py-0.5 text-xs rounded ${sourceBadgeColor[pkg.source] || "bg-gray-100"}`}>
                              {pkg.source}
                            </span>
                          </td>
                          <td className="py-2">
                            <button
                              onClick={() => handleRemove(pkg)}
                              className="text-red-500 hover:text-red-700 text-xs"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                      {installedPackages.length === 0 && (
                        <tr><td colSpan={4} className="text-center py-4 text-gray-400">No packages</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Install Modal */}
          {installTarget && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg shadow-xl p-6 w-96">
                <h3 className="font-semibold text-lg mb-4">Install Package</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-500">Package</label>
                    <p className="font-medium">{installTarget.name} ({installTarget.version})</p>
                  </div>
                  <div>
                    <label className="text-sm text-gray-500">Source</label>
                    <p className="font-medium">{installTarget.source}</p>
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 block mb-1">Target Environment</label>
                    <select
                      value={installEnv}
                      onChange={(e) => setInstallEnv(e.target.value)}
                      className="w-full border rounded px-3 py-2 text-sm"
                    >
                      {environments.map((env) => (
                        <option key={env.name} value={env.name}>{env.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex gap-2 mt-6">
                  <button
                    onClick={handleInstall}
                    disabled={installing}
                    className="flex-1 bg-bioaf-600 text-white py-2 rounded text-sm hover:bg-bioaf-700 disabled:opacity-50"
                  >
                    {installing ? "Installing..." : "Confirm Install"}
                  </button>
                  <button
                    onClick={() => setInstallTarget(null)}
                    className="flex-1 border py-2 rounded text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
