import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, ChevronLeft, ChevronRight, AlertCircle } from "lucide-react";
import { documentService } from "../services/documentService";
import UploadDropzone from "../components/UploadDropzone";
import DocumentCard from "../components/DocumentCard";
import LoadingSkeleton from "../components/LoadingSkeleton";
import EmptyState from "../components/EmptyState";

export default function Documents() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const size = 9; // Grid size

  // Query documents list
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["documents", page, search],
    queryFn: () => documentService.listDocuments(page, size),
    // Poll list every 5s if any document is in "processing" status
    refetchInterval: (query) => {
      const docs = query.state.data?.items ?? [];
      const hasProcessing = docs.some((doc) => doc.status.toLowerCase() === "processing");
      return hasProcessing ? 5000 : false;
    },
  });

  const documents = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.pages ?? 1;

  // Filter documents locally by search query as well (just in case)
  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(search.toLowerCase())
  );

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => documentService.uploadDocuments(files),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["recent-documents"] });
      // In package.json, we have sonner, let's use a simple window alert or standard toast if available
      // Standard toast: import { toast } from "sonner"
    },
    onError: (err) => {
      console.error("Upload failed", err);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["recent-documents"] });
    },
    onError: (err) => {
      console.error("Delete failed", err);
    },
  });

  const handleUpload = (files: File[]) => {
    uploadMutation.mutate(files);
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this document? This will remove all database chunks and vector indices.")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
          Document Management
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Ingest and organize your research papers. Ingested papers are chunked and vectorized instantly.
        </p>
      </div>

      {/* ── Upload Section ──────────────────────────────────────── */}
      <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
          Ingest New Document
        </h2>
        <UploadDropzone
          onUpload={handleUpload}
          isUploading={uploadMutation.isPending}
        />
      </div>

      {/* ── Document List Toolbar & Grid ────────────────────────── */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-zinc-100 dark:border-zinc-900 pb-4">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            Ingested Papers Library ({total})
          </h2>

          {/* Search bar */}
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1); // Reset page on search
              }}
              placeholder="Search by filename..."
              className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 outline-none rounded-lg pl-9 pr-4 py-2 text-xs transition-colors focus:border-zinc-400 dark:focus:border-zinc-600"
            />
          </div>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="card" count={3} />
        ) : filteredDocs.length === 0 ? (
          <EmptyState
            title={search ? "No search results" : "Your library is empty"}
            description={
              search
                ? `No documents match "${search}". Try searching for another filename.`
                : "Drop PDF, DOCX, or TXT files above to compile your research collection."
            }
          />
        ) : (
          <>
            {/* Grid layout for DocumentCards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredDocs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onDelete={handleDelete}
                  isDeleting={deleteMutation.isPending && deleteMutation.variables === doc.id}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-4 pt-4">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 rounded-lg text-zinc-500 disabled:opacity-40 cursor-pointer"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-zinc-500 font-medium">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 rounded-lg text-zinc-500 disabled:opacity-40 cursor-pointer"
                  aria-label="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
