import React from "react";
import { FolderOpen, Upload, MessageSquare, Sparkles, ChevronRight } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, description, action }: EmptyStateProps) {
  const isLibraryEmpty = title.toLowerCase().includes("empty") || title.toLowerCase().includes("no ready");

  if (isLibraryEmpty) {
    return (
      <div className="flex flex-col items-center justify-center p-8 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-950 py-12 shadow-sm">
        <div className="max-w-3xl w-full text-center space-y-8">
          <div className="space-y-2">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
              Get Started with PaperForge
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-md mx-auto">
              Follow these three simple steps to unlock the power of grounded research synthesis.
            </p>
          </div>

          {/* Stepper Cards Container */}
          <div className="grid grid-cols-1 md:grid-cols-5 items-center gap-4 pt-4">
            
            {/* Step 1 */}
            <div className="md:col-span-1 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/10 text-center space-y-3 h-full flex flex-col justify-start">
              <div className="h-10 w-10 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 flex items-center justify-center mx-auto shadow-sm">
                <Upload className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">1. Upload Paper</p>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-450 leading-relaxed">
                  Drop PDF, DOCX, or TXT files above to vectorize them instantly.
                </p>
              </div>
            </div>

            {/* Arrow 1 */}
            <div className="md:col-span-1 flex items-center justify-center text-zinc-300 dark:text-zinc-700">
              <ChevronRight className="h-5 w-5 rotate-90 md:rotate-0" />
            </div>

            {/* Step 2 */}
            <div className="md:col-span-1 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/10 text-center space-y-3 h-full flex flex-col justify-start">
              <div className="h-10 w-10 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-850 dark:text-zinc-150 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center mx-auto shadow-sm">
                <MessageSquare className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">2. Ask Questions</p>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-450 leading-relaxed">
                  Query PaperForge Grounding workspace using literature evidence.
                </p>
              </div>
            </div>

            {/* Arrow 2 */}
            <div className="md:col-span-1 flex items-center justify-center text-zinc-300 dark:text-zinc-700">
              <ChevronRight className="h-5 w-5 rotate-90 md:rotate-0" />
            </div>

            {/* Step 3 */}
            <div className="md:col-span-1 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/10 text-center space-y-3 h-full flex flex-col justify-start">
              <div className="h-10 w-10 rounded-xl bg-zinc-150 dark:bg-zinc-800 text-zinc-850 dark:text-zinc-150 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center mx-auto shadow-sm">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">3. Save Insights</p>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-450 leading-relaxed">
                  Save evidence insights and export note workspaces.
                </p>
              </div>
            </div>

          </div>

          {action && <div className="pt-2">{action}</div>}
        </div>
      </div>
    );
  }

  // Fallback for standard search-not-found / error empty states
  return (
    <div className="flex flex-col items-center justify-center text-center p-8 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 py-16 shadow-sm">
      <div className="h-12 w-12 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center mb-4">
        <FolderOpen className="h-6 w-6 text-zinc-400 dark:text-zinc-500" />
      </div>
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-1">
        {title}
      </h3>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mb-5 leading-relaxed">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}
