import React, { useState, KeyboardEvent } from "react";
import { Send, ArrowUp } from "lucide-react";

interface PromptInputProps {
  onSend: (text: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  selectedDocCount?: number;
}

export default function PromptInput({
  onSend,
  isLoading = false,
  disabled = false,
  selectedDocCount = 0,
}: PromptInputProps) {
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (trimmed && !isLoading && !disabled) {
      onSend(trimmed);
      setText("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-950 p-3 hover:border-zinc-300 dark:hover:border-zinc-700 focus-within:ring-1 focus-within:ring-zinc-400 dark:focus-within:ring-zinc-600 transition-all duration-200">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={
          selectedDocCount > 0
            ? `Ask PaperForge about the ${selectedDocCount} selected document(s)...`
            : "Select documents on the left and ask a question..."
        }
        className="w-full resize-none outline-none border-none text-sm text-zinc-900 dark:text-zinc-50 bg-transparent min-h-[60px] max-h-[200px]"
        disabled={disabled || isLoading}
      />

      <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-900 pt-2.5 mt-2">
        {/* Scope details */}
        <div className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium">
          {selectedDocCount > 0 ? (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Grounded QA scoped to {selectedDocCount} document(s)
            </span>
          ) : (
            <span className="flex items-center gap-1 text-amber-500">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-ping" />
              Select at least one document on the left to ask
            </span>
          )}
        </div>

        {/* Submit action */}
        <button
          onClick={handleSend}
          disabled={!text.trim() || isLoading || disabled || selectedDocCount === 0}
          className="h-8 w-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-950 flex items-center justify-center transition-colors cursor-pointer disabled:opacity-30 disabled:hover:bg-zinc-900 dark:disabled:hover:bg-zinc-100"
          aria-label="Send query"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
