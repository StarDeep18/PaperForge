import React from "react";

interface ConfidenceBadgeProps {
  confidence: string;
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const normalized = confidence.toLowerCase();

  const getConfig = () => {
    switch (normalized) {
      case "high":
        return {
          bg: "bg-emerald-50 dark:bg-emerald-950/30",
          text: "text-emerald-700 dark:text-emerald-400",
          border: "border-emerald-200 dark:border-emerald-900/50",
          label: "High Grounding Confidence",
        };
      case "medium":
        return {
          bg: "bg-zinc-50 dark:bg-zinc-900/40",
          text: "text-zinc-700 dark:text-zinc-300",
          border: "border-zinc-200 dark:border-zinc-800",
          label: "Medium Grounding Confidence",
        };
      case "low":
      default:
        return {
          bg: "bg-amber-50 dark:bg-amber-950/30",
          text: "text-amber-700 dark:text-amber-400",
          border: "border-amber-200 dark:border-amber-900/50",
          label: "Low Grounding Confidence",
        };
    }
  };

  const config = getConfig();

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border text-xs font-semibold ${config.bg} ${config.text} ${config.border}`}
    >
      {config.label}
    </span>
  );
}
