import React from "react";
import { Link2, FileText, ChevronRight } from "lucide-react";
import { Citation } from "../types";

interface CitationCardProps {
  citation: Citation;
  index: number;
  isActive?: boolean;
  onClick?: () => void;
}

export default function CitationCard({
  citation,
  index,
  isActive = false,
  onClick,
}: CitationCardProps) {
  return (
    <div
      onClick={onClick}
      className={`border rounded-xl p-4 transition-all duration-200 cursor-pointer ${
        isActive
          ? "border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-900/40"
          : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/20"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="h-5 w-5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 flex items-center justify-center text-[10px] font-bold border border-zinc-200 dark:border-zinc-700 flex-shrink-0">
            {index}
          </span>
          <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate min-w-0">
            {citation.document_title}
          </h4>
        </div>

        <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium whitespace-nowrap">
          {citation.pages.length > 0 ? `Pages: ${citation.pages.join(", ")}` : "No Page info"}
        </span>
      </div>

      {/* Snippet supporting content */}
      <div className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed line-clamp-3 bg-zinc-50/50 dark:bg-zinc-900/30 p-2.5 rounded-lg border border-zinc-100/50 dark:border-zinc-900/20 mb-2">
        {citation.supporting_chunks?.[0] || "Supporting evidence text unavailable."}
      </div>

      <div className="flex items-center justify-between text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold uppercase tracking-wider mt-2.5">
        <span className="flex items-center gap-1">
          <Link2 className="h-3 w-3" />
          <span>Grounding Confidence: {citation.confidence}</span>
        </span>
        <span className="flex items-center gap-0.5 text-zinc-500 dark:text-zinc-300">
          View Detail
          <ChevronRight className="h-3 w-3" />
        </span>
      </div>
    </div>
  );
}
