import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  FileText,
  Brain,
  Upload,
  PlusCircle,
  Activity,
  Database,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { documentService } from "../services/documentService";
import { healthService } from "../services/healthService";
import StatusBadge from "../components/StatusBadge";
import LoadingSkeleton from "../components/LoadingSkeleton";

export default function Dashboard() {
  // Query health check status
  const {
    data: health,
    isLoading: healthLoading,
    refetch: refetchHealth,
    isRefetching: healthRefetching,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => healthService.checkHealth(),
    refetchInterval: 30000, // Refresh every 30s
  });

  // Query documents count and list (fetch 5 items)
  const { data: docData, isLoading: docsLoading } = useQuery({
    queryKey: ["recent-documents"],
    queryFn: () => documentService.listDocuments(1, 5),
  });

  const totalDocuments = docData?.total ?? 0;
  const recentDocs = docData?.items ?? [];

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Welcome Title Block */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
            Welcome to PaperForge
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Analyze, chunk, embed, and query research papers in a dedicated RAG workspace.
          </p>
        </div>
      </div>

      {/* ── Key Statistics Row ──────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Documents Count */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 flex items-center justify-between shadow-sm">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
              Total Ingested Papers
            </span>
            <h2 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
              {totalDocuments}
            </h2>
          </div>
          <div className="h-12 w-12 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center text-zinc-500">
            <FileText className="h-6 w-6" />
          </div>
        </div>

        {/* Workspace Quick-jump */}
        <Link
          to="/workspace"
          className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 flex items-center justify-between shadow-sm hover:border-zinc-300 dark:hover:border-zinc-700 transition-all duration-200 group"
        >
          <div className="space-y-1">
            <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
              AI Grounding Workspace
            </span>
            <div className="flex items-center gap-1.5 font-bold text-zinc-900 dark:text-zinc-50 text-xl mt-1.5">
              <span>Open Workspace</span>
              <ArrowRight className="h-4 w-4 text-zinc-400 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
          <div className="h-12 w-12 rounded-xl bg-zinc-950 dark:bg-zinc-50 flex items-center justify-center text-white dark:text-zinc-900">
            <Brain className="h-6 w-6" />
          </div>
        </Link>

        {/* System Health Check Audit summary */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 flex items-center justify-between shadow-sm">
          <div className="space-y-1 min-w-0">
            <span className="text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
              <span>System Integrity</span>
              <button
                onClick={() => refetchHealth()}
                disabled={healthRefetching}
                className="text-zinc-400 hover:text-zinc-600 cursor-pointer disabled:opacity-40"
                aria-label="Refresh health audit"
              >
                <RefreshCw className={`h-3 w-3 ${healthRefetching ? "animate-spin" : ""}`} />
              </button>
            </span>
            <div className="mt-1">
              {healthLoading ? (
                <div className="h-6 w-20 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
              ) : (
                <StatusBadge status={health?.overall_status ?? "Healthy"} />
              )}
            </div>
          </div>
          <div className="h-12 w-12 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center text-zinc-500">
            <Activity className="h-6 w-6" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Left/Center: Recent Documents ───────────────────────── */}
        <div className="lg:col-span-2 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-900 pb-3">
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50">
              Recently Ingested Papers
            </h3>
            <Link
              to="/documents"
              className="text-xs text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200 font-medium flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {docsLoading ? (
            <LoadingSkeleton type="table" />
          ) : recentDocs.length === 0 ? (
            <div className="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">
              No research papers ingested yet. Click "Upload" to begin.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="text-zinc-400 dark:text-zinc-500 font-semibold border-b border-zinc-100 dark:border-zinc-900 pb-2">
                    <th className="py-2.5">File Name</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Chunks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900 text-zinc-700 dark:text-zinc-300">
                  {recentDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/10">
                      <td className="py-3.5 font-medium truncate max-w-[240px]">
                        {doc.original_filename}
                      </td>
                      <td>{formatSize(doc.file_size)}</td>
                      <td>
                        <StatusBadge status={doc.status} size="sm" />
                      </td>
                      <td className="font-semibold text-zinc-900 dark:text-zinc-50">
                        {doc.chunk_count || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Right: Services Auditing Status Details ─────────────── */}
        <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="border-b border-zinc-100 dark:border-zinc-900 pb-3">
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50">
              Audits Health Details
            </h3>
          </div>

          {healthLoading ? (
            <LoadingSkeleton type="table" />
          ) : (
            <div className="space-y-3.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Upload Service</span>
                <StatusBadge status={health?.upload_service ?? "Healthy"} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Parsing Engine</span>
                <StatusBadge status={health?.parser ?? "Healthy"} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Embedding AI Provider</span>
                <StatusBadge status={health?.embedding_provider ?? "Healthy"} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Chroma Vector Store</span>
                <StatusBadge status={health?.vector_store ?? "Healthy"} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Retrieval Service</span>
                <StatusBadge status={health?.retrieval ?? "Healthy"} size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">LLM Generation Provider</span>
                <StatusBadge status={health?.generation ?? "Healthy"} size="sm" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
