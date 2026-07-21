import React, { useState, useEffect } from "react";
import { Link } from "react-router";
import {
  BookOpen,
  Search,
  Download,
  Trash2,
  Calendar,
  Sparkles,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { useNotes } from "../hooks/useNotes";

export default function Notes() {
  const { notes, updateNote, deleteNote, exportNotes, fetchNotes } = useNotes();
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchNotes();
  }, []);

  const filteredNotes = notes.filter(
    (note) =>
      note.note.toLowerCase().includes(search.toLowerCase()) ||
      note.snippet.toLowerCase().includes(search.toLowerCase()) ||
      note.documentTitle.toLowerCase().includes(search.toLowerCase())
  );

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return "Unknown Date";
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-zinc-700 dark:text-zinc-300" />
            <span>Research Notes Library</span>
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Consolidate scientific insights, ground evidence passages, annotate literature, and compile research summaries.
          </p>
        </div>

        {notes.length > 0 && (
          <button
            onClick={exportNotes}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-950 text-xs font-semibold rounded-xl shadow-sm transition-colors cursor-pointer self-start sm:self-center"
          >
            <Download className="h-4 w-4" />
            <span>Export Notes as MD</span>
          </button>
        )}
      </div>

      {/* Toolbar */}
      {notes.length > 0 && (
        <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-900 pb-4">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            Saved Literature Insights ({filteredNotes.length})
          </h2>

          <div className="relative w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes, quotes, or paper names..."
              className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 outline-none rounded-lg pl-9 pr-4 py-2 text-xs transition-colors focus:border-zinc-400 dark:focus:border-zinc-600"
            />
          </div>
        </div>
      )}

      {/* Main Grid View */}
      {notes.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center p-8 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-950 py-20 shadow-sm">
          <div className="h-14 w-14 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center mb-6">
            <BookOpen className="h-7 w-7 text-zinc-400 dark:text-zinc-500" />
          </div>
          <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            Your notes library is empty
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mb-6 leading-relaxed">
            Save core text passages directly from citation cards or the interactive PDF drawer in the grounding workspace.
          </p>
          <Link
            to="/workspace"
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-950 text-xs font-semibold rounded-xl shadow-sm transition-colors cursor-pointer"
          >
            <span>Go to Grounding Workspace</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : filteredNotes.length === 0 ? (
        <div className="text-center py-16 text-zinc-400 dark:text-zinc-500 text-xs">
          No research notes match your search query.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredNotes.map((note) => (
            <div
              key={note.id}
              className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 flex flex-col justify-between shadow-sm space-y-4 hover:shadow-md transition-shadow duration-200"
            >
              <div className="space-y-4">
                
                {/* Header card details */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-100 dark:bg-zinc-850 text-zinc-800 dark:text-zinc-200 border border-zinc-200/50 dark:border-zinc-700/50">
                      Page {note.pageNumber}
                    </span>
                    <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-50 leading-snug line-clamp-2 mt-1">
                      {note.documentTitle}
                    </h3>
                  </div>

                  <button
                    onClick={() => deleteNote(note.id)}
                    className="p-1.5 hover:bg-red-50 dark:hover:bg-red-950/20 text-zinc-400 hover:text-red-500 rounded-lg transition-colors cursor-pointer flex-shrink-0"
                    aria-label="Delete note"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {/* Extracted snippet passage */}
                <div className="bg-zinc-50/50 dark:bg-zinc-900/20 border border-zinc-100 dark:border-zinc-900/50 p-3.5 rounded-xl text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed italic relative">
                  <Sparkles className="h-3.5 w-3.5 text-zinc-350 dark:text-zinc-650 absolute -top-1.5 -left-1.5 bg-white dark:bg-zinc-950 rounded-full p-0.5" />
                  <p className="line-clamp-4">{note.snippet}</p>
                </div>

                {/* Edit Annotation Notes */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                    My Annotations
                  </span>
                  <textarea
                    value={note.note}
                    onChange={(e) => updateNote(note.id, e.target.value)}
                    placeholder="Write your custom notes, annotations, or analysis thoughts here..."
                    className="w-full bg-zinc-50/30 dark:bg-zinc-900/10 border border-zinc-100 dark:border-zinc-900/50 rounded-xl p-3 text-xs outline-none focus:border-zinc-300 dark:focus:border-zinc-700 min-h-[90px] resize-none focus:bg-white dark:focus:bg-zinc-950 transition-colors leading-relaxed placeholder-zinc-400"
                  />
                </div>

              </div>

              {/* Note Footer */}
              <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-900 pt-3 text-[10px] text-zinc-400 dark:text-zinc-500 font-medium">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{formatTime(note.createdAt)}</span>
                </div>

                <Link
                  to="/workspace"
                  onClick={() => {
                    // Open this doc/citation direct in workspace
                    localStorage.setItem("paperforge_scoping_focus_doc", note.documentId);
                    window.dispatchEvent(
                      new CustomEvent("paperforge-focus-doc", {
                        detail: { id: note.documentId, filename: note.documentTitle },
                      })
                    );
                  }}
                  className="flex items-center gap-1 text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
                >
                  <span>Open Paper</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}
