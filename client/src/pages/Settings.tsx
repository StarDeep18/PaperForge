import React from "react";
import { Settings, Shield, Sliders, Database, Info, Sun, Moon } from "lucide-react";
import { useTheme } from "../hooks/useTheme";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
          Settings
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Manage application themes, view workspace parameters, and verify storage limits.
        </p>
      </div>

      <div className="space-y-6">
        {/* Theme Preferences */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-100 dark:border-zinc-900 pb-3">
            <Sun className="h-4 w-4 text-zinc-500" />
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50">
              Aesthetics & Theme
            </h3>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="space-y-1">
              <p className="font-medium text-zinc-800 dark:text-zinc-200">
                Application Theme Mode
              </p>
              <p className="text-zinc-400 dark:text-zinc-500">
                Select color palette preference for research screens.
              </p>
            </div>
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 px-3.5 py-2 rounded-xl font-medium cursor-pointer transition-colors duration-150"
            >
              {theme === "light" ? (
                <>
                  <Moon className="h-4 w-4 text-zinc-700" />
                  <span>Switch to Dark</span>
                </>
              ) : (
                <>
                  <Sun className="h-4 w-4 text-zinc-300" />
                  <span>Switch to Light</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Ingestion Parameters Overview */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-100 dark:border-zinc-900 pb-3">
            <Sliders className="h-4 w-4 text-zinc-500" />
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50">
              RAG Pipeline Configuration Parameters
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-zinc-700 dark:text-zinc-300">
            <div className="space-y-1 bg-zinc-50/50 dark:bg-zinc-900/10 border border-zinc-100 dark:border-zinc-900 p-3.5 rounded-xl">
              <p className="font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider text-[10px]">
                Chunking Configuration
              </p>
              <div className="flex justify-between pt-1">
                <span>Standard Chunk Size</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">512 tokens</span>
              </div>
              <div className="flex justify-between">
                <span>Overlap Margin</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">50 tokens</span>
              </div>
            </div>

            <div className="space-y-1 bg-zinc-50/50 dark:bg-zinc-900/10 border border-zinc-100 dark:border-zinc-900 p-3.5 rounded-xl">
              <p className="font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider text-[10px]">
                Retrieval Configuration
              </p>
              <div className="flex justify-between pt-1">
                <span>Query Top K Chunks</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">8 results</span>
              </div>
              <div className="flex justify-between">
                <span>Cosine Similarity Cutoff</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">0.30 score</span>
              </div>
            </div>
          </div>
        </div>

        {/* Security & Access Panel */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-100 dark:border-zinc-900 pb-3">
            <Shield className="h-4 w-4 text-zinc-500" />
            <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-50">
              Access & Security
            </h3>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="space-y-1">
              <p className="font-medium text-zinc-800 dark:text-zinc-200">
                Workspace Ownership
              </p>
              <p className="text-zinc-400 dark:text-zinc-500">
                User ID: <code className="bg-zinc-100 dark:bg-zinc-900 px-1.5 py-0.5 rounded font-mono text-[10px]">user-123</code>
              </p>
            </div>
            <span className="bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 px-3 py-1.5 rounded-xl font-semibold text-zinc-600 dark:text-zinc-300">
              Owner Account
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
