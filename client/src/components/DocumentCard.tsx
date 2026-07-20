import React from "react";
import { File, Trash2, Calendar, HardDrive, FileSpreadsheet } from "lucide-react";
import { Document } from "../types";
import StatusBadge from "./StatusBadge";

interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => void;
  isDeleting?: boolean;
}

export default function DocumentCard({
  document,
  onDelete,
  isDeleting = false,
}: DocumentCardProps) {
  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Format date string
  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="group border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-950 p-5 hover:shadow-sm transition-all duration-200 flex flex-col justify-between h-48">
      <div>
        {/* Header containing title and delete controls */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-10 w-10 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center flex-shrink-0">
              <File className="h-5 w-5 text-zinc-500 dark:text-zinc-400" />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-sm text-zinc-900 dark:text-zinc-100 truncate group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
                {document.original_filename}
              </h3>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 truncate">
                {document.metadata.title || "No metadata title extracted"}
              </p>
            </div>
          </div>

          <button
            onClick={() => onDelete(document.id)}
            disabled={isDeleting}
            className="p-1.5 text-zinc-400 hover:text-rose-600 dark:text-zinc-500 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20 rounded-lg transition-colors cursor-pointer"
            aria-label="Delete document"
          >
            <Trash2 className={`h-4 w-4 ${isDeleting ? "animate-pulse" : ""}`} />
          </button>
        </div>

        {/* Authors and status row */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <StatusBadge status={document.status} size="sm" />
          {document.metadata.authors && document.metadata.authors.length > 0 && (
            <span className="text-[10px] bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 px-2 py-0.5 rounded-full text-zinc-500 dark:text-zinc-400 truncate max-w-[120px]">
              {document.metadata.authors.join(", ")}
            </span>
          )}
        </div>
      </div>

      {/* Footer details (file sizes, chunking metrics, metadata tags) */}
      <div className="flex items-center justify-between text-xs text-zinc-400 dark:text-zinc-500 pt-3 border-t border-zinc-100 dark:border-zinc-900">
        <span className="flex items-center gap-1.5">
          <HardDrive className="h-3.5 w-3.5" />
          <span>{formatSize(document.file_size)}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <FileSpreadsheet className="h-3.5 w-3.5" />
          <span>{document.chunk_count || 0} chunks</span>
        </span>
        <span className="flex items-center gap-1.5">
          <Calendar className="h-3.5 w-3.5" />
          <span>{formatDate(document.created_at)}</span>
        </span>
      </div>
    </div>
  );
}
