import React from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import {
  LayoutDashboard,
  FileText,
  Brain,
  Settings,
  Sun,
  Moon,
  Search,
  ChevronDown,
  Database,
} from "lucide-react";
import { useTheme } from "../hooks/useTheme";

export default function DashboardLayout() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  // Mock total storage usage computed from API stats
  const storageUsage = "18.4 MB";
  const storageLimit = "500 MB";
  const storagePercentage = 3.6;

  // Active navigation helper
  const getNavLinkClass = ({ isActive }: { isActive: boolean }) => {
    const base =
      "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200";
    if (isActive) {
      return `${base} bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50`;
    }
    return `${base} text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50`;
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50 font-sans transition-colors duration-200">
      {/* ── Left Sidebar ────────────────────────────────────────── */}
      <aside className="w-64 border-r border-zinc-200 dark:border-zinc-800 flex flex-col justify-between h-full bg-zinc-50/50 dark:bg-zinc-900/30">
        <div>
          {/* Logo Section */}
          <div className="h-16 flex items-center gap-2.5 px-6 border-b border-zinc-200 dark:border-zinc-800">
            <div className="h-8 w-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center">
              <Brain className="h-5 w-5 text-white dark:text-zinc-900" />
            </div>
            <span className="font-semibold text-lg tracking-tight">PaperForge</span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <NavLink to="/dashboard" className={getNavLinkClass}>
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </NavLink>
            <NavLink to="/documents" className={getNavLinkClass}>
              <FileText className="h-4 w-4" />
              <span>Documents</span>
            </NavLink>
            <NavLink to="/workspace" className={getNavLinkClass}>
              <Brain className="h-4 w-4" />
              <span>Workspace</span>
            </NavLink>
            <NavLink to="/settings" className={getNavLinkClass}>
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </NavLink>
          </nav>
        </div>

        {/* Storage display at the bottom */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-900/50 m-4 rounded-xl">
          <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400 mb-2">
            <span className="flex items-center gap-1.5 font-medium">
              <Database className="h-3.5 w-3.5" />
              <span>Storage Used</span>
            </span>
            <span>{storageUsage}</span>
          </div>
          <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1.5 mb-2 overflow-hidden">
            <div
              className="bg-zinc-900 dark:bg-zinc-100 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${storagePercentage}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-zinc-400 dark:text-zinc-500 block">
            Plan limit: {storageLimit}
          </span>
        </div>
      </aside>

      {/* ── Main Area ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between px-6 bg-white dark:bg-zinc-950">
          {/* Search bar placeholder */}
          <div className="relative w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
            <input
              type="text"
              placeholder="Search workspaces..."
              className="w-full bg-zinc-100/70 hover:bg-zinc-100 dark:bg-zinc-900/60 dark:hover:bg-zinc-900 border-none outline-none rounded-lg pl-9 pr-4 py-2 text-sm transition-all focus:ring-1 focus:ring-zinc-400 focus:bg-white dark:focus:bg-zinc-900"
              disabled
            />
          </div>

          {/* Right Header Navigation Panel */}
          <div className="flex items-center gap-4">
            {/* Workspace Selector */}
            <div className="flex items-center gap-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors duration-150">
              <span>Main Workspace</span>
              <ChevronDown className="h-3 w-3 text-zinc-400" />
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 rounded-lg text-zinc-500 dark:text-zinc-400 cursor-pointer transition-colors duration-150"
              aria-label="Toggle theme"
            >
              {theme === "light" ? (
                <Moon className="h-4 w-4 text-zinc-700" />
              ) : (
                <Sun className="h-4 w-4 text-zinc-300" />
              )}
            </button>

            {/* Profile Avatar */}
            <div className="h-8 w-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center font-semibold text-xs text-zinc-600 dark:text-zinc-300 select-none">
              DS
            </div>
          </div>
        </header>

        {/* Content Outlet View */}
        <main className="flex-1 overflow-auto bg-zinc-50/20 dark:bg-zinc-950/20">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
