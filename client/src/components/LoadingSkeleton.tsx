import React from "react";

interface LoadingSkeletonProps {
  type?: "card" | "chat" | "table" | "sidebar";
  count?: number;
}

export default function LoadingSkeleton({
  type = "card",
  count = 3,
}: LoadingSkeletonProps) {
  const renderSkeleton = () => {
    switch (type) {
      case "chat":
        return (
          <div className="space-y-4 p-5">
            <div className="flex gap-4 items-start animate-pulse">
              <div className="h-8 w-8 rounded-lg bg-zinc-200 dark:bg-zinc-800" />
              <div className="flex-1 space-y-2">
                <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded w-1/4" />
                <div className="h-3.5 bg-zinc-200 dark:bg-zinc-800 rounded w-3/4" />
                <div className="h-3.5 bg-zinc-200 dark:bg-zinc-800 rounded w-1/2" />
              </div>
            </div>
          </div>
        );
      case "table":
        return (
          <div className="w-full space-y-3 p-4 animate-pulse">
            <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded-lg w-full" />
            <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded-lg w-full" />
            <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded-lg w-full" />
          </div>
        );
      case "card":
      default:
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {Array.from({ length: count }).map((_, idx) => (
              <div
                key={idx}
                className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 bg-white dark:bg-zinc-950 flex flex-col justify-between h-48 animate-pulse"
              >
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="h-10 w-10 rounded-lg bg-zinc-200 dark:bg-zinc-800" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3 bg-zinc-200 dark:bg-zinc-800 rounded w-3/4" />
                      <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded w-1/2" />
                    </div>
                  </div>
                </div>
                <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded w-full mt-4" />
              </div>
            ))}
          </div>
        );
    }
  };

  return <>{renderSkeleton()}</>;
}
