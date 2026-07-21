import React from "react";
import { useAuth } from "../context/AuthProvider";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { User, Mail, Calendar, FileText, BookOpen, Clock, Activity, Loader2 } from "lucide-react";

interface MeResponse {
  email: string;
  display_name: string;
  statistics: {
    documents_count: number;
    notes_count: number;
    timeline_events_count: number;
  };
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
    statistics: { documents_count: 0, notes_count: 0, timeline_events_count: 0 },
  };

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-950 p-6 md:p-8 space-y-8 transition-colors">
      
      {/* Page Title */}
      <div className="flex items-center gap-3 border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <div className="h-10 w-10 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-zinc-500 shadow-sm">
          <User className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-black text-zinc-900 dark:text-zinc-50 tracking-tight">
            My Profile
          </h1>
          <p className="text-xs text-zinc-450 dark:text-zinc-500">
            Manage your account credentials and see workspace stats
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Profile Card */}
        <div className="md:col-span-1 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-6 shadow-sm flex flex-col items-center text-center space-y-4">
          <div className="h-20 w-20 rounded-full bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-white dark:text-zinc-950 text-2xl font-black shadow-inner">
            {getInitials(profile.display_name)}
          </div>
          <div>
            <h3 className="font-black text-lg text-zinc-900 dark:text-zinc-50 leading-tight">
              {profile.display_name}
            </h3>
            <span className="text-xs text-zinc-400 dark:text-zinc-500 uppercase tracking-wider font-semibold">
              Research Fellow
            </span>
          </div>

          <div className="w-full border-t border-zinc-100 dark:border-zinc-800 pt-4 space-y-3.5 text-xs text-left">
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <Mail className="h-4 w-4 shrink-0 text-zinc-400" />
              <span className="truncate">{profile.email}</span>
            </div>
            <div className="flex items-center gap-2.5 text-zinc-650 dark:text-zinc-400">
              <Calendar className="h-4 w-4 shrink-0 text-zinc-400" />
              <span>Created: {formatDate(currentUser?.metadata.creationTime)}</span>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-4 h-fit">
          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-lg bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center border border-zinc-150 dark:border-zinc-800 text-zinc-500">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Total Papers Ingested
              </span>
              <span className="text-3xl font-black text-zinc-900 dark:text-zinc-50">
                {profile.statistics.documents_count}
              </span>
            </div>
          </div>

          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-lg bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center border border-zinc-150 dark:border-zinc-800 text-amber-500">
              <BookOpen className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Saved Notes & Insights
              </span>
              <span className="text-3xl font-black text-zinc-900 dark:text-zinc-50">
                {profile.statistics.notes_count}
              </span>
            </div>
          </div>

          <div className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-4">
            <div className="h-9 w-9 rounded-lg bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center border border-zinc-150 dark:border-zinc-800 text-emerald-500">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">
                Timeline Events Logged
              </span>
              <span className="text-3xl font-black text-zinc-900 dark:text-zinc-50">
                {profile.statistics.timeline_events_count}
              </span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
