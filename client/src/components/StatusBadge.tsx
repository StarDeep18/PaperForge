import React from "react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export default function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const normalized = status.toLowerCase();

  const getStatusConfig = () => {
    switch (normalized) {
      case "ready":
      case "healthy":
      case "success":
        return {
          bg: "bg-emerald-50 dark:bg-emerald-950/30",
          text: "text-emerald-700 dark:text-emerald-400",
          border: "border-emerald-200 dark:border-emerald-900/50",
          dot: "bg-emerald-500",
          label: "Ready",
        };
      case "processing":
      case "pending":
        return {
          bg: "bg-amber-50 dark:bg-amber-950/30",
          text: "text-amber-700 dark:text-amber-400",
          border: "border-amber-200 dark:border-amber-900/50",
          dot: "bg-amber-500 animate-pulse",
          label: "Processing",
        };
      case "failed":
      case "unhealthy":
      case "error":
        return {
          bg: "bg-rose-50 dark:bg-rose-950/30",
          text: "text-rose-700 dark:text-rose-400",
          border: "border-rose-200 dark:border-rose-900/50",
          dot: "bg-rose-500",
          label: "Failed",
        };
      default:
        return {
          bg: "bg-zinc-50 dark:bg-zinc-800",
          text: "text-zinc-600 dark:text-zinc-300",
          border: "border-zinc-200 dark:border-zinc-700",
          dot: "bg-zinc-400",
          label: status,
        };
    }
  };

  const config = getStatusConfig();
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses} select-none`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      <span>{config.label}</span>
    </span>
  );
}
