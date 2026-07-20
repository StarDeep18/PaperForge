import React from "react";
import { User, Brain } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  onCitationClick?: (citationId: string) => void;
}

export default function ChatMessage({
  role,
  content,
  onCitationClick,
}: ChatMessageProps) {
  const isUser = role === "user";

  // Preprocess text to format citation links [1] into custom markdown markers
  // or inline clickable superscripts.
  const renderMessageContent = () => {
    if (isUser) {
      return <p className="text-sm whitespace-pre-wrap leading-relaxed text-zinc-800 dark:text-zinc-200">{content}</p>;
    }

    // Preprocess [1] markers to custom internal link markdown
    const processedContent = content.replace(/\[(\d+)\]/g, "[$1](#cite-$1)");

    const components = {
      a(props: any) {
        const href = props.href || "";
        if (href.startsWith("#cite-")) {
          const num = href.replace("#cite-", "");
          return (
            <button
              onClick={() => onCitationClick?.(num)}
              className="inline-flex items-center justify-center h-3.5 min-w-[14px] px-0.5 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-900 dark:text-zinc-100 rounded text-[9px] font-bold align-super cursor-pointer border border-zinc-200 dark:border-zinc-700 select-none mx-0.5 transform -translate-y-0.5 transition-colors"
            >
              {num}
            </button>
          );
        }
        return <a {...props} />;
      }
    };

    return (
      <div className="prose dark:prose-invert max-w-none text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
        <ReactMarkdown components={components}>{processedContent}</ReactMarkdown>
      </div>
    );
  };

  return (
    <div
      className={`flex gap-4 p-5 ${
        isUser
          ? "bg-white dark:bg-zinc-950"
          : "bg-zinc-50/50 dark:bg-zinc-900/10 border-y border-zinc-100 dark:border-zinc-900/50"
      }`}
    >
      {/* Icon Avatar */}
      <div
        className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isUser
            ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300"
            : "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Brain className="h-4 w-4" />}
      </div>

      {/* Message Content Bubble */}
      <div className="flex-1 min-w-0 mt-0.5">
        <div className="text-[10px] uppercase tracking-wider text-zinc-400 dark:text-zinc-500 font-semibold mb-1">
          {isUser ? "User Query" : "PaperForge AI"}
        </div>
        {renderMessageContent()}
      </div>
    </div>
  );
}
