import React, { useState, useEffect, useRef, KeyboardEvent } from "react";
import { useNavigate } from "react-router";
import {
  Search,
  FileText,
  MessageSquare,
  Sparkles,
  BookOpen,
  Sun,
  Moon,
  Upload,
  RefreshCw,
  X,
  Command,
} from "lucide-react";
import { useTheme } from "../hooks/useTheme";
import { useNotes } from "../hooks/useNotes";
import { documentService } from "../services/documentService";
import { useQuery } from "@tanstack/react-query";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommandItem {
  id: string;
  category: "Actions" | "Documents" | "Chats" | "Citations" | "Notes";
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  action: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { notes } = useNotes();
  const [search, setSearch] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch documents list for search autocomplete
  const { data: docData } = useQuery({
    queryKey: ["command-palette-documents"],
    queryFn: () => documentService.listDocuments(1, 100),
    enabled: isOpen,
  });
  const allDocuments = docData?.items ?? [];
  const readyDocuments = allDocuments.filter((d) => d.status.toLowerCase() === "ready");

  // Load chat messages from localStorage to search chats/citations
  const getChatHistory = () => {
    try {
      const stored = localStorage.getItem("paperforge_current_chat_messages");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };
  const chatMessages = getChatHistory();

  // Reset index when search query changes
  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  // Handle escape to close, and keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: any) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Build list of items based on query
  const items: CommandItem[] = [];

  const addAction = (title: string, subtitle: string, icon: React.ReactNode, action: () => void) => {
    items.push({
      id: `action-${title.toLowerCase().replace(/\s+/g, "-")}`,
      category: "Actions",
      title,
      subtitle,
      icon,
      action: () => {
        action();
        onClose();
      },
    });
  };

  if (!search.trim()) {
    // Default actions
    addAction("Go to Dashboard", "Navigate to overview dashboard", <FileText className="h-4 w-4" />, () => navigate("/dashboard"));
    addAction("Go to Workspace", "Open the AI grounded research workspace", <Sparkles className="h-4 w-4" />, () => navigate("/workspace"));
    addAction("Go to Documents Library", "Ingest and manage PDF research papers", <FileText className="h-4 w-4" />, () => navigate("/documents"));
    addAction("Go to Research Notes", "View saved scientific insights and annotations", <BookOpen className="h-4 w-4" />, () => navigate("/notes"));
    addAction("Toggle Light/Dark Theme", `Switch system theme (currently ${theme})`, theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />, () => toggleTheme());
    addAction("Start New Chat", "Reset current grounding workspace chat session", <RefreshCw className="h-4 w-4" />, () => {
      localStorage.removeItem("paperforge_current_chat_messages");
      // Dispatch custom event to let Workspace page know to reload chat
      window.dispatchEvent(new Event("paperforge-new-chat"));
      navigate("/workspace");
    });
    addAction("Upload Research Paper", "Navigate and focus document ingest uploader", <Upload className="h-4 w-4" />, () => {
      navigate("/documents");
      setTimeout(() => {
        const dropzone = document.querySelector(".border-dashed");
        if (dropzone) (dropzone as HTMLElement).click();
      }, 300);
    });
  } else {
    const q = search.toLowerCase();

    // 1. Documents search
    readyDocuments
      .filter((doc) => doc.original_filename.toLowerCase().includes(q) || doc.metadata?.title?.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((doc) => {
        items.push({
          id: `doc-${doc.id}`,
          category: "Documents",
          title: doc.original_filename,
          subtitle: doc.metadata?.title || "No document title details",
          icon: <FileText className="h-4 w-4 text-zinc-500" />,
          action: () => {
            // Select this document in workspace and open it
            localStorage.setItem("paperforge_scoping_focus_doc", doc.id);
            window.dispatchEvent(new CustomEvent("paperforge-focus-doc", { detail: { id: doc.id, filename: doc.original_filename } }));
            navigate("/workspace");
            onClose();
          },
        });
      });

    // 2. Chat history search
    chatMessages
      .filter((msg: any) => msg.content.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((msg: any, idx: number) => {
        items.push({
          id: `chat-${idx}`,
          category: "Chats",
          title: msg.content,
          subtitle: msg.role === "user" ? "User query statement" : "Assistant response synthesis",
          icon: <MessageSquare className="h-4 w-4 text-emerald-500" />,
          action: () => {
            navigate("/workspace");
            onClose();
          },
        });
      });

    // 3. Citations search
    const allCitations: any[] = [];
    chatMessages.forEach((msg: any) => {
      if (msg.citations && Array.isArray(msg.citations)) {
        msg.citations.forEach((cite: any) => {
          if (!allCitations.some((c) => c.document_id === cite.document_id && c.formatted_reference === cite.formatted_reference)) {
            allCitations.push(cite);
          }
        });
      }
    });

    allCitations
      .filter((cite) => cite.document_title.toLowerCase().includes(q) || (cite.supporting_chunks?.[0]?.toLowerCase() || "").includes(q))
      .slice(0, 5)
      .forEach((cite, idx) => {
        items.push({
          id: `cite-${idx}`,
          category: "Citations",
          title: cite.document_title,
          subtitle: cite.supporting_chunks?.[0] || "No cited text snippet details",
          icon: <Sparkles className="h-4 w-4 text-amber-500" />,
          action: () => {
            localStorage.setItem("paperforge_open_citation_direct", JSON.stringify(cite));
            window.dispatchEvent(new CustomEvent("paperforge-open-citation", { detail: cite }));
            navigate("/workspace");
            onClose();
          },
        });
      });

    // 4. Notes search
    notes
      .filter((note) => note.note.toLowerCase().includes(q) || note.snippet.toLowerCase().includes(q) || note.documentTitle.toLowerCase().includes(q))
      .slice(0, 5)
      .forEach((note) => {
        items.push({
          id: `note-${note.id}`,
          category: "Notes",
          title: note.note || "Untitled Annotation",
          subtitle: `Quote: "${note.snippet.substring(0, 60)}..."`,
          icon: <BookOpen className="h-4 w-4 text-violet-500" />,
          action: () => {
            navigate("/notes");
            onClose();
          },
        });
      });
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % Math.max(1, items.length));
      // Scroll list item into view if needed
      setTimeout(() => {
        const selectedEl = listRef.current?.querySelector(".bg-zinc-100, .dark\\:bg-zinc-800");
        selectedEl?.scrollIntoView({ block: "nearest" });
      }, 10);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + items.length) % Math.max(1, items.length));
      setTimeout(() => {
        const selectedEl = listRef.current?.querySelector(".bg-zinc-100, .dark\\:bg-zinc-800");
        selectedEl?.scrollIntoView({ block: "nearest" });
      }, 10);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (items[activeIndex]) {
        items[activeIndex].action();
      }
    }
  };

  // Group items by category for rendering
  const categories: Record<string, CommandItem[]> = {};
  items.forEach((item) => {
    categories[item.category] = categories[item.category] || [];
    categories[item.category].push(item);
  });

  // Calculate absolute flat index to map hover events
  let flatIndexCounter = 0;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
      {/* Backdrop blur overlay */}
      <div className="fixed inset-0 bg-zinc-950/40 backdrop-blur-md" onClick={onClose} />

      {/* Modal Dialog container */}
      <div className="relative bg-white/90 dark:bg-zinc-900/90 backdrop-blur-xl border border-zinc-200 dark:border-zinc-800 shadow-2xl rounded-2xl max-w-xl w-full max-h-[480px] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Search header bar */}
        <div className="flex items-center gap-3 px-4 border-b border-zinc-200 dark:border-zinc-800 h-14 flex-shrink-0">
          <Search className="h-4 w-4 text-zinc-400 dark:text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type to search papers, chats, insights, or notes..."
            className="flex-1 bg-transparent border-none outline-none text-sm text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 dark:placeholder-zinc-500"
            autoFocus
          />
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-700 uppercase tracking-wider flex items-center gap-1">
              <Command className="h-2.5 w-2.5" />
              <span>K</span>
            </span>
            <button onClick={onClose} className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors cursor-pointer">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Scrollable list viewport */}
        <div ref={listRef} className="flex-1 overflow-y-auto p-2 space-y-3">
          {items.length === 0 ? (
            <div className="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">
              No results found matching "{search}"
            </div>
          ) : (
            Object.entries(categories).map(([category, catItems]) => (
              <div key={category} className="space-y-1">
                {/* Category tag */}
                <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider px-3 py-1 block">
                  {category}
                </span>

                {/* Items list mapping */}
                {catItems.map((item) => {
                  const currentIndex = flatIndexCounter++;
                  const isSelected = activeIndex === currentIndex;

                  return (
                    <div
                      key={item.id}
                      onClick={item.action}
                      onMouseEnter={() => setActiveIndex(currentIndex)}
                      className={`flex items-center justify-between gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all duration-150 ${
                        isSelected
                          ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                          : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/40"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`h-8 w-8 rounded-lg flex items-center justify-center border transition-colors flex-shrink-0 ${
                          isSelected
                            ? "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-700"
                            : "bg-zinc-50 dark:bg-zinc-900 border-transparent text-zinc-400 dark:text-zinc-500"
                        }`}>
                          {item.icon}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold truncate leading-tight">
                            {item.title}
                          </p>
                          {item.subtitle && (
                            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 truncate mt-0.5 max-w-[420px]">
                              {item.subtitle}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      {isSelected && (
                        <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium whitespace-nowrap">
                          Press Enter ↵
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
