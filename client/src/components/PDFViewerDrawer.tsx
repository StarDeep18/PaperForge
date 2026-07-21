import React, { useState, useEffect } from "react";
import { X, BookOpen, Sparkles, Check } from "lucide-react";
import { useNotes } from "../hooks/useNotes";
import { toast } from "sonner";

interface PDFViewerDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentTitle: string;
  pageNumber: number;
  snippet?: string;
}

export default function PDFViewerDrawer({
  isOpen,
  onClose,
  documentId,
  documentTitle,
  pageNumber,
  snippet = "",
}: PDFViewerDrawerProps) {
  const { notes, addNote } = useNotes();
  const [annotation, setAnnotation] = useState("");
  const [isSaved, setIsSaved] = useState(false);

  // Check if this snippet is already saved in notes
  useEffect(() => {
    if (!isOpen) return;
    const exists = notes.some(
      (n) => n.documentId === documentId && n.snippet === snippet
    );
    setIsSaved(exists);
    setAnnotation("");
  }, [isOpen, documentId, snippet, notes]);

  const handleSaveInsight = () => {
    if (!snippet) return;
    
    addNote({
      documentId,
      documentTitle,
      pageNumber,
      snippet,
      note: annotation,
    });
    
    setIsSaved(true);
    toast.success("Insight saved directly to Research Notes!");
  };

  // Construct PDF URL pointing to local proxy server with page jump hash
  const pdfUrl = `/api/v1/documents/${documentId}/file#page=${pageNumber}`;

  return (
    <div
      className={`fixed inset-y-0 right-0 z-40 w-[45vw] min-w-[450px] max-w-[800px] bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-800 shadow-2xl flex flex-col h-full transition-transform duration-300 ease-in-out ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {/* Header banner */}
      <div className="h-16 flex items-center justify-between px-6 border-b border-zinc-200 dark:border-zinc-800 flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <BookOpen className="h-5 w-5 text-zinc-500 flex-shrink-0" />
          <div className="min-w-0">
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50 truncate">
              {documentTitle}
            </h3>
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold uppercase tracking-wider mt-0.5">
              Source Grounding Page {pageNumber}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors cursor-pointer"
          aria-label="Close panel"
        >
          <X className="h-4.5 w-4.5" />
        </button>
      </div>

      {/* Scrollable contents drawer */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Cited grounding text passage */}
        {snippet && (
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Cited Grounding Passage</span>
            </h4>
            <div className="bg-zinc-50/50 dark:bg-zinc-900/30 border border-zinc-150 dark:border-zinc-850 p-4 rounded-xl text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed italic relative">
              <span className="text-3xl text-zinc-200 dark:text-zinc-800 font-serif absolute -top-2 left-2 pointer-events-none">“</span>
              <p className="pl-4 relative z-10">{snippet}</p>
            </div>
          </div>
        )}

        {/* Save Insight annotation note editor */}
        <div className="bg-zinc-50/30 dark:bg-zinc-900/10 border border-zinc-100 dark:border-zinc-900/50 p-4 rounded-2xl space-y-3">
          <h4 className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
            {isSaved ? "Saved in Research Notes" : "Annotate & Save Insight"}
          </h4>
          
          {isSaved ? (
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100/50 dark:border-emerald-900/20 p-2.5 rounded-lg">
              <Check className="h-4 w-4" />
              <span>Saved successfully to Research Notes (Edit in Notes page)</span>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={annotation}
                onChange={(e) => setAnnotation(e.target.value)}
                placeholder="Add custom annotations, summary notes, or research remarks to attach to this insight..."
                className="w-full resize-none bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-850 rounded-xl p-3 text-xs outline-none focus:border-zinc-400 dark:focus:border-zinc-700 min-h-[70px] placeholder-zinc-400 dark:placeholder-zinc-500"
              />
              <button
                onClick={handleSaveInsight}
                disabled={!snippet}
                className="w-full bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-950 text-xs font-semibold py-2 rounded-xl transition-colors cursor-pointer disabled:opacity-40 disabled:hover:bg-zinc-900"
              >
                Save Insight to Workspace Notes
              </button>
            </div>
          )}
        </div>

        {/* PDF viewer iframe container */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
            PDF Document Preview
          </h4>
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden bg-zinc-100 dark:bg-zinc-900">
            <iframe
              src={pdfUrl}
              className="w-full h-[450px]"
              title="Grounding PDF preview page"
            />
          </div>
        </div>

      </div>
    </div>
  );
}
