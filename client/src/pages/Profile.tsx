import React from "react";
import { useAuth } from "../context/AuthProvider";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { User, Mail, Calendar, FileText, BookOpen, Clock, Activity, HardDrive, MessageSquare, Layers, FolderKanban, Loader2 } from "lucide-react";

interface ProfileStatistics {
  workspace_name: string;
  storage_used_bytes: number;
  storage_used_formatted: str;
  documents_count: number;
  questions_asked_count: number;
  notes_saved_count: number;
  research_sessions_count: number;
  last_login?: string;
}

interface MeResponse {
  email: string;
  display_name: string;
  statistics: ProfileStatistics;
}

export default function Profile() {
  const { currentUser } = useAuth();

  const { data, isLoading } = useQuery<MeResponse>({
    queryKey: ["auth-me"],
    queryFn: async () => {
      const response = await api.get<MeResponse>("/auth/me");
      return response.data;
    },
  });

  const getInitials = (name: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Unknown";
    return new Date(dateString).toLocaleDateString([], {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return "Active now";
    return new Date(dateString).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 bg-zinc-50 dark:bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
          <span className="text-xs text-zinc-500 font-semibold">Loading profile information...</span>
        </div>
      </div>
    );
  }

  const profile = data || {
    email: currentUser?.email || "user@example.com",
    display_name: currentUser?.displayName || "Research User",
    statistics: {
      workspace_name: "Primary Research Workspace",
      storage_used_bytes: 0,
      storage_used_formatted: "0 KB",
      documents_count: 0,
      questions_asked_count: 0,
      notes_saved_count: 0,
      research_sessions_count: 0,
      last_login: undefined,
    },
  };

  const stats = profile.statistics;

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-950 p-6 md:p-8 space-y-8 transition-colors">
      
      {/* Page Title */}
      <div className="flex items-center gap-3 border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <div className="h-10 w-10 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-zinc-500 shadow-sm">
          <User className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-black text-zinc-900 dark:text-zinc-50 tracking-tight">
            My Profile & Workspace
          </h1>
          <p className="text-xs text-zinc-450 dark:text-zinc-500">
            Account credentials, active tenant scope, and live storage statistics
          </p>
        </div>
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Profile Info Card */}
        <div className="md:col-span-1 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="h-20 w-20 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white text-2xl font-black shadow-lg">
              {getInitials(profile.display_name)}
            </div>
            <div>
              <h3 className="font-black text-lg text-zinc-900 dark:text-zinc-50 leading-tight">
                {profile.display_name}
              </h3>
              <span className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 px-2.5 py-0.5 rounded-full border border-indigo-150 dark:border-indigo-800 inline-block mt-1">
                Research Fellow
              </span>
            </div>
          </div>

          <div className="w-full border-t border-zinc-100 dark:border-zinc-800 pt-4 space-y-3.5 text-xs">
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <Mail className="h-4 w-4 shrink-0 text-zinc-400" />
              <span className="truncate">{profile.email}</span>
            </div>
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <FolderKanban className="h-4 w-4 shrink-0 text-zinc-400" />
              <span className="font-medium text-zinc-800 dark:text-zinc-200">{stats.workspace_name}</span>
            </div>
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <Calendar className="h-4 w-4 shrink-0 text-zinc-400" />
              <span>Created: {formatDate(currentUser?.metadata.creationTime)}</span>
            </div>
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <Clock className="h-4 w-4 shrink-0 text-emerald-500" />
              <span>Last Login: {formatDateTime(stats.last_login)}</span>
            </div>
          </div>
        </div>

        {/* Stats Cards Grid */}
        <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 h-fit">
          
          {/* Storage Used */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center border border-blue-150 dark:border-blue-800 text-blue-600 dark:text-blue-400">
              <HardDrive className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Storage Used
              </span>
              <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">
                {stats.storage_used_formatted}
              </span>
            </div>
          </div>

          {/* Documents */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-violet-50 dark:bg-violet-950/50 flex items-center justify-center border border-violet-150 dark:border-violet-800 text-violet-600 dark:text-violet-400">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Documents Ingested
              </span>
              <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">
                {stats.documents_count}
              </span>
            </div>
          </div>

          {/* Questions Asked */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 flex items-center justify-center border border-emerald-150 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400">
              <MessageSquare className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Questions Asked
              </span>
              <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">
                {stats.questions_asked_count}
              </span>
            </div>
          </div>

          {/* Notes Saved */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-amber-50 dark:bg-amber-950/50 flex items-center justify-center border border-amber-150 dark:border-amber-800 text-amber-600 dark:text-amber-400">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Notes Saved
              </span>
              <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">
                {stats.notes_saved_count}
              </span>
            </div>
          </div>

          {/* Research Sessions */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-rose-50 dark:bg-rose-950/50 flex items-center justify-center border border-rose-150 dark:border-rose-800 text-rose-600 dark:text-rose-400">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Research Sessions
              </span>
              <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">
                {stats.research_sessions_count}
              </span>
            </div>
          </div>

          {/* Workspace Status */}
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-xl bg-teal-50 dark:bg-teal-950/50 flex items-center justify-center border border-teal-150 dark:border-teal-800 text-teal-600 dark:text-teal-400">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                System Status
              </span>
              <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 mt-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Operational
              </span>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

