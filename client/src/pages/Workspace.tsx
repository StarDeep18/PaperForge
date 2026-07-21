import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  FileText,
  Layers,
  ChevronRight,
  Brain,
  Search,
  MessageSquare,
  AlertCircle,
  HelpCircle,
  Sparkles,
} from "lucide-react";
import { documentService } from "../services/documentService";
import { chatService } from "../services/chatService";
import ChatMessage from "../components/ChatMessage";
import PromptInput from "../components/PromptInput";
import CitationCard from "../components/CitationCard";
import ConfidenceBadge from "../components/ConfidenceBadge";
import EmptyState from "../components/EmptyState";
import LoadingSkeleton from "../components/LoadingSkeleton";
import { Citation, ChatResponse } from "../types";
import PDFViewerDrawer from "../components/PDFViewerDrawer";
import { useNotes } from "../hooks/useNotes";
import { addTimelineEvent } from "../hooks/useTimeline";
import { BookOpen, Download, Trash2 } from "lucide-react";
import { useWorkspaceSettings } from "../hooks/useWorkspaceSettings";
import { api } from "../services/api";

export default function Workspace() {
  const [searchQuery, setSearchQuery] = useState("");
  const { settings, updateSettings } = useWorkspaceSettings();
  const selectedDocIds = settings.selected_document_ids || [];
  const setSelectedDocIds = (ids: string[] | ((prev: string[]) => string[])) => {
    if (typeof ids === "function") {
      updateSettings({ selected_document_ids: ids(selectedDocIds) });
    } else {
      updateSettings({ selected_document_ids: ids });
    }
  };

  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string; citations?: Citation[]; confidence?: string; evidence?: any[] }>>([]);

  // Load conversation history when active conversation changes
  useEffect(() => {
    if (settings.active_conversation_id) {
      api.get(`/chat/conversations/${settings.active_conversation_id}`)
        .then((res) => {
          const mapped = res.data.map((m: any) => ({
            role: m.role,
            content: m.content,
            citations: m.citations,
            confidence: m.confidence || "High",
            evidence: m.evidence || [],
          }));
          setMessages(mapped);
        })
        .catch((err) => {
          console.error("Failed to fetch conversation history:", err);
        });
    } else {
      setMessages([]);
    }
  }, [settings.active_conversation_id]);
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);
  const [activePDF, setActivePDF] = useState<{
    documentId: string;
    documentTitle: string;
    pageNumber: number;
    snippet?: string;
  } | null>(null);

  const { notes, updateNote, deleteNote, exportNotes, fetchNotes } = useNotes();
  const [rightPanelTab, setRightPanelTab] = useState<"grounding" | "notes">("grounding");

  // Fetch notes from backend on mount
  useEffect(() => {
    fetchNotes();
  }, []);

  // Global keyboard shortcuts and Command Palette integration listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActivePDF(null);
      }
      if (e.key === "/") {
        const tag = document.activeElement?.tagName;
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          e.preventDefault();
          const promptArea = document.getElementById("chat-prompt-textarea");
          promptArea?.focus();
        }
      }
    };

    const handleFocusDoc = (e: Event) => {
      const doc = (e as CustomEvent).detail;
      if (doc && doc.id) {
        setSelectedDocIds((prev) => (prev.includes(doc.id) ? prev : [...prev, doc.id]));
        setActivePDF({
          documentId: doc.id,
          documentTitle: doc.filename,
          pageNumber: 1,
          snippet: "",
        });
      }
    };

    const handleOpenCitation = (e: Event) => {
      const cite = (e as CustomEvent).detail;
      if (cite && cite.document_id) {
        setSelectedDocIds((prev) => (prev.includes(cite.document_id) ? prev : [...prev, cite.document_id]));
        setActivePDF({
          documentId: cite.document_id,
          documentTitle: cite.document_title,
          pageNumber: cite.pages?.[0] || 1,
          snippet: cite.supporting_chunks?.[0] || "",
        });
      }
    };

    const handleNewChat = () => {
      setMessages([]);
      useWorkspaceSettings.getState().updateSettings({ active_conversation_id: "" });
    };

    const handleNoteSavedRedirect = () => {
      setRightPanelTab("notes");
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("paperforge-focus-doc", handleFocusDoc);
    window.addEventListener("paperforge-open-citation", handleOpenCitation);
    window.addEventListener("paperforge-new-chat", handleNewChat);
    window.addEventListener("paperforge-note-saved-redirect", handleNoteSavedRedirect);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("paperforge-focus-doc", handleFocusDoc);
      window.removeEventListener("paperforge-open-citation", handleOpenCitation);
      window.removeEventListener("paperforge-new-chat", handleNewChat);
      window.removeEventListener("paperforge-note-saved-redirect", handleNoteSavedRedirect);
    };
  }, []);

  // References for automatic scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const citationRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Query available ready documents
  const { data: docData, isLoading: docsLoading } = useQuery({
    queryKey: ["workspace-documents"],
    queryFn: () => documentService.listDocuments(1, 100), // load up to 100 documents
  });

  const allDocuments = docData?.items ?? [];
  const readyDocuments = allDocuments.filter((doc) => doc.status.toLowerCase() === "ready");

  // Filter documents locally
  const filteredDocs = readyDocuments.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Auto-select all documents by default if none are chosen yet
  useEffect(() => {
    if (readyDocuments.length > 0 && selectedDocIds.length === 0) {
      setSelectedDocIds(readyDocuments.map((doc) => doc.id));
    }
  }, [readyDocuments]);

  // Scroll to chat bottom when a message is added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Chat QA Mutation
  const chatMutation = useMutation({
    mutationFn: (query: string) => {
      // Map message history to schema format
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Scoping query to selected documents using custom retrieval option metadata
      return chatService.sendMessage({
        query,
        conversation_id: settings.active_conversation_id || undefined,
        conversation_history: history,
        retrieval_options: {
          document_ids: selectedDocIds, // Scopes retrieval only to selected document records!
          top_k: 5,
        },
      });
    },
    onSuccess: (data: ChatResponse, queryText: string) => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          confidence: data.confidence,
          evidence: data.evidence_graph?.nodes ?? [],
        },
      ]);
      
      const convId = data.conversation_id || data.conversationId;
      if (convId && convId !== settings.active_conversation_id) {
        updateSettings({ active_conversation_id: convId });
      }

      const truncatedQuery = queryText.length > 55 ? queryText.substring(0, 55) + "..." : queryText;
      addTimelineEvent("ask_question", `Asked: "${truncatedQuery}"`);
    },
    onError: (err) => {
      console.error("Chat request failed", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error while processing your request. Please ensure the backend server is running and try again.",
        },
      ]);
    },
  });

  const handleSendPrompt = (text: string) => {
    // 1. Append user message locally
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    // 2. Trigger grounding AI request
    chatMutation.mutate(text);
  };

  const handleToggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleSelectAllDocs = () => {
    if (selectedDocIds.length === readyDocuments.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(readyDocuments.map((doc) => doc.id));
    }
  };

  // Scroll to active citation card, highlight it, and open PDF viewer drawer
  const handleCitationClick = (citationNum: string) => {
    setActiveCitationId(citationNum);
    const element = citationRefs.current[citationNum];
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // Load PDF drawer with this citation's specific page/grounding snippet
    const idx = parseInt(citationNum) - 1;
    const citeData = currentCitations[idx];
    if (citeData) {
      setActivePDF({
        documentId: citeData.document_id,
        documentTitle: citeData.document_title,
        pageNumber: citeData.pages?.[0] || 1,
        snippet: citeData.supporting_chunks?.[0] || "",
      });
    }

    // Auto-reset highlight flash after 2 seconds
    setTimeout(() => {
      setActiveCitationId(null);
    }, 2000);
  };

  // Extract last assistant message references for right panel rendering
  const lastAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.citations);

  const currentCitations = lastAssistantMessage?.citations ?? [];
  const currentConfidence = lastAssistantMessage?.confidence ?? "";
  const currentEvidence = lastAssistantMessage?.evidence ?? [];

  return (
    <div className="h-[calc(100vh-64px)] w-full grid grid-cols-12 overflow-hidden bg-zinc-50/10 dark:bg-zinc-950/10 font-sans">
      
      {/* ── LEFT COLUMN: Documents & Collections Panel ───────────── */}
      <div className="col-span-3 border-r border-zinc-200 dark:border-zinc-800 flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
        
        {/* Upper Pane: Documents scoping list */}
        <div className="flex-1 flex flex-col h-1/2 min-h-0 border-b border-zinc-200 dark:border-zinc-800 p-4">
          <div className="flex items-center justify-between mb-3.5">
            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-50 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="h-4 w-4 text-zinc-500" />
              <span>Reference Scope ({filteredDocs.length})</span>
            </span>
            <button
              onClick={handleSelectAllDocs}
              className="text-[10px] text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 font-semibold cursor-pointer"
            >
              {selectedDocIds.length === readyDocuments.length ? "Deselect All" : "Select All"}
            </button>
          </div>

          {/* Quick Search bar */}
          <div className="relative mb-3 flex-shrink-0">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reference library..."
              className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 outline-none rounded-lg pl-8 pr-3 py-1.5 text-xs transition-colors focus:border-zinc-400"
            />
          </div>

          {/* Documents scoping list content */}
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {docsLoading ? (
              <div className="space-y-2 py-4">
                <div className="h-6 bg-zinc-100 dark:bg-zinc-900 rounded animate-pulse" />
                <div className="h-6 bg-zinc-100 dark:bg-zinc-900 rounded animate-pulse" />
                <div className="h-6 bg-zinc-100 dark:bg-zinc-900 rounded animate-pulse" />
              </div>
            ) : filteredDocs.length === 0 ? (
              <div className="text-center py-8 text-zinc-400 dark:text-zinc-500 text-xs">
                {searchQuery ? "No matching papers found." : "No ready research papers found."}
              </div>
            ) : (
              filteredDocs.map((doc) => (
                <label
                  key={doc.id}
                  className={`flex items-center gap-2.5 p-2 rounded-lg border text-xs cursor-pointer select-none transition-colors duration-150 ${
                    selectedDocIds.includes(doc.id)
                      ? "border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/30"
                      : "border-transparent hover:bg-zinc-50 dark:hover:bg-zinc-900/10 text-zinc-500"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={() => handleToggleDocSelection(doc.id)}
                    className="accent-zinc-900 dark:accent-zinc-100 rounded"
                  />
                  <span className="truncate font-medium flex-1">{doc.original_filename}</span>
                </label>
              ))
            )}
          </div>
        </div>

        {/* Lower Pane: Collections/Folders Placeholder */}
        <div className="flex-1 flex flex-col h-1/2 min-h-0 p-4 bg-zinc-50/20 dark:bg-zinc-950/20">
          <span className="text-xs font-bold text-zinc-900 dark:text-zinc-50 uppercase tracking-wider flex items-center gap-1.5 mb-4">
            <Layers className="h-4 w-4 text-zinc-500" />
            <span>Collections</span>
          </span>

          <div className="flex-1 flex flex-col items-center justify-center text-center p-4 border border-zinc-200/55 dark:border-zinc-850 border-dashed rounded-xl bg-white/40 dark:bg-zinc-900/10">
            <Layers className="h-5 w-5 text-zinc-300 dark:text-zinc-700 mb-2" />
            <p className="text-[10px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
              Coming Soon
            </p>
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-1 max-w-[150px]">
              Group related research papers into custom scoping folders.
            </p>
          </div>
        </div>
      </div>

      {/* ── CENTER COLUMN: AI QA Chat Interface ───────────────────── */}
      <div className="col-span-6 flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
        
        {/* Chat Thread Container */}
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-900">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-8">
              <div className="max-w-md text-center space-y-4">
                <div className="h-12 w-12 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-950 flex items-center justify-center mx-auto shadow-sm">
                  <Brain className="h-6 w-6" />
                </div>
                <h2 className="text-base font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
                  Research Grounding Workspace
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  Ask questions scoped directly to your reference library. PaperForge will synthesize answers grounded in evidence from the active texts.
                </p>
                <div className="grid grid-cols-2 gap-3 text-left pt-4">
                  <div className="border border-zinc-100 dark:border-zinc-900 p-3 rounded-xl bg-zinc-50/50 dark:bg-zinc-900/30">
                    <p className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase">Grounded QA</p>
                    <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1">Answers include source citations map to paper sections.</p>
                  </div>
                  <div className="border border-zinc-100 dark:border-zinc-900 p-3 rounded-xl bg-zinc-50/50 dark:bg-zinc-900/30">
                    <p className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase">Scoping</p>
                    <p className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1">Deselect documents to filter references in search queries.</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <ChatMessage
                  key={index}
                  role={msg.role}
                  content={msg.content}
                  onCitationClick={handleCitationClick}
                />
              ))}

              {/* Streaming loading indicators */}
              {chatMutation.isPending && (
                <div className="flex gap-4 p-5 bg-zinc-50/50 dark:bg-zinc-900/10 border-y border-zinc-100 dark:border-zinc-900/50 animate-pulse">
                  <div className="h-8 w-8 rounded-lg bg-zinc-200 dark:bg-zinc-800 flex-shrink-0" />
                  <div className="flex-1 space-y-2 mt-0.5">
                    <div className="h-2.5 bg-zinc-200 dark:bg-zinc-800 rounded w-24" />
                    <div className="h-3 bg-zinc-200 dark:bg-zinc-800 rounded w-full" />
                    <div className="h-3 bg-zinc-200 dark:bg-zinc-800 rounded w-5/6" />
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested prompts list */}
        {readyDocuments.length > 0 && selectedDocIds.length > 0 && (
          <div className="px-4 py-2 border-t border-zinc-150 dark:border-zinc-900/60 bg-zinc-50/20 dark:bg-zinc-950/20 flex gap-2 overflow-x-auto scrollbar-none items-center scrollbar-thin">
            <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider whitespace-nowrap mr-1 flex items-center gap-1 flex-shrink-0">
              <Sparkles className="h-3 w-3" /> Suggestions:
            </span>
            {selectedDocIds.length > 1 ? (
              <>
                <button
                  onClick={() => handleSendPrompt("Compare the research methodologies, architectures, and theoretical foundations used across these papers.")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  📊 Compare Methodologies
                </button>
                <button
                  onClick={() => handleSendPrompt("Provide a comparative analysis of the evaluation datasets, benchmarks, metrics, and empirical performance results.")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  🏆 Compare Results
                </button>
                <button
                  onClick={() => handleSendPrompt("What are the key research gaps, conflicts, unresolved questions, or future directions identified between these works?")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  🔍 Identify Research Gaps
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => handleSendPrompt("Summarize the primary contributions, core thesis, and novel claims of this research paper.")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  📝 Summarize Contributions
                </button>
                <button
                  onClick={() => handleSendPrompt("Explain the technical methodology, algorithms, model design, and experimental setup detailed in this paper.")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  ⚙️ Explain Methodology
                </button>
                <button
                  onClick={() => handleSendPrompt("What are the limitations, assumptions, failures, or critical arguments against the claims in this paper?")}
                  className="px-2.5 py-1 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 rounded-lg text-[10px] font-semibold text-zinc-650 dark:text-zinc-350 cursor-pointer whitespace-nowrap transition-colors"
                >
                  ⚠️ Identify Limitations
                </button>
              </>
            )}
          </div>
        )}

        {/* Floating Chat Input */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
          <PromptInput
            onSend={handleSendPrompt}
            isLoading={chatMutation.isPending}
            disabled={selectedDocIds.length === 0}
            selectedDocCount={selectedDocIds.length}
          />
        </div>
      </div>

      {/* ── RIGHT COLUMN: Integrated Evidence & Grounding citations / Research Notes ── */}
      <div className="col-span-3 border-l border-zinc-200 dark:border-zinc-800 flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
        
        {/* Right Panel Tabs navigation header */}
        <div className="flex border-b border-zinc-200 dark:border-zinc-800 flex-shrink-0 bg-zinc-55/30">
          <button
            onClick={() => setRightPanelTab("grounding")}
            className={`flex-1 py-3.5 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 border-b-2 transition-colors cursor-pointer ${
              rightPanelTab === "grounding"
                ? "border-zinc-900 text-zinc-900 dark:border-zinc-100 dark:text-zinc-50 bg-zinc-50/20 dark:bg-zinc-950/10"
                : "border-transparent text-zinc-400 dark:text-zinc-500 hover:text-zinc-650"
            }`}
          >
            <Sparkles className="h-4 w-4" />
            <span>Grounding ({currentCitations.length})</span>
          </button>
          <button
            onClick={() => setRightPanelTab("notes")}
            className={`flex-1 py-3.5 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 border-b-2 transition-colors cursor-pointer ${
              rightPanelTab === "notes"
                ? "border-zinc-900 text-zinc-900 dark:border-zinc-100 dark:text-zinc-50 bg-zinc-50/20 dark:bg-zinc-950/10"
                : "border-transparent text-zinc-400 dark:text-zinc-500 hover:text-zinc-650"
            }`}
          >
            <BookOpen className="h-4 w-4" />
            <span>Workspace Notes ({notes.filter((n) => selectedDocIds.includes(n.documentId)).length})</span>
          </button>
        </div>

        {/* Tab content view mapping */}
        {rightPanelTab === "grounding" ? (
          <div className="flex-1 flex flex-col min-h-0 divide-y divide-zinc-200 dark:divide-zinc-800">
            {/* Upper Pane: EvidenceStatements Log */}
            <div className="flex-1 flex flex-col h-1/2 min-h-0 p-4">
              <span className="text-[10px] font-bold text-zinc-450 dark:text-zinc-550 uppercase tracking-wider flex items-center gap-1.5 mb-3.5">
                <Sparkles className="h-3.5 w-3.5 text-zinc-450" />
                <span>Extracted Evidence ({currentEvidence.length})</span>
              </span>

              <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 text-xs">
                {messages.length === 0 ? (
                  <div className="text-center py-12 text-zinc-400 dark:text-zinc-500">
                    Send a question to compile supporting evidence graphs.
                  </div>
                ) : currentEvidence.length === 0 ? (
                  <div className="text-center py-12 text-zinc-400 dark:text-zinc-500">
                    No statement-level evidence generated for this answer.
                  </div>
                ) : (
                  currentEvidence.map((node, idx) => (
                    <div
                      key={idx}
                      className="p-3 border border-zinc-100 dark:border-zinc-900 rounded-xl bg-zinc-50/50 dark:bg-zinc-900/30"
                    >
                      <p className="font-semibold text-zinc-850 dark:text-zinc-250 leading-relaxed mb-1.5">
                        {node.statement}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold uppercase">
                        <span>Evidence confidence</span>
                        <span className={node.confidence > 0.7 ? "text-emerald-500" : "text-amber-500"}>
                          {(node.confidence * 100).toFixed(0)}% Match
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Lower Pane: Grounding Citations Library */}
            <div className="flex-1 flex flex-col h-1/2 min-h-0 p-4">
              <div className="flex items-center justify-between mb-3.5">
                <span className="text-[10px] font-bold text-zinc-450 dark:text-zinc-555 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-zinc-455" />
                  <span>Grounding Sources ({currentCitations.length})</span>
                </span>

                {currentConfidence && <ConfidenceBadge confidence={currentConfidence} />}
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                {messages.length === 0 ? (
                  <div className="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">
                    Citations list will appear here when answers are processed.
                  </div>
                ) : currentCitations.length === 0 ? (
                  <div className="text-center py-12 text-zinc-400 dark:text-zinc-500 text-xs">
                    Answer is based on general training dataset without citations.
                  </div>
                ) : (
                  currentCitations.map((cite, index) => {
                    const citeNum = cite.citation_id || String(index + 1);
                    return (
                      <div
                        key={citeNum}
                        ref={(el) => {
                          citationRefs.current[citeNum] = el;
                        }}
                        className="transition-all duration-300"
                      >
                        <CitationCard
                          citation={cite}
                          index={index + 1}
                          isActive={activeCitationId === citeNum}
                          onClick={() => handleCitationClick(citeNum)}
                        />
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Tab 2: Integrated notes scoped to selected documents */
          <div className="flex-1 flex flex-col min-h-0 p-4 bg-zinc-50/20 dark:bg-zinc-950/25">
            {/* Header info & export */}
            <div className="flex items-center justify-between gap-3 mb-4 flex-shrink-0">
              <span className="text-[10px] font-bold text-zinc-450 dark:text-zinc-500 uppercase tracking-wider">
                Session Scientific Notes
              </span>
              {notes.filter((n) => selectedDocIds.includes(n.documentId)).length > 0 && (
                <button
                  onClick={exportNotes}
                  className="flex items-center gap-1 px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-950 rounded-lg text-[10px] font-bold shadow-sm transition-colors cursor-pointer"
                >
                  <Download className="h-3 w-3" />
                  <span>Export notes</span>
                </button>
              )}
            </div>

            {/* Notes scroll list */}
            <div className="flex-1 overflow-y-auto space-y-3.5 pr-1">
              {notes.filter((n) => selectedDocIds.includes(n.documentId)).length === 0 ? (
                <div className="text-center py-12 text-zinc-450 dark:text-zinc-550 text-xs space-y-2">
                  <p>No research notes saved for active documents.</p>
                  <p className="text-[10px] text-zinc-400">
                    Click "Save Insight" in citation cards or the PDF Viewer drawer to capture notes.
                  </p>
                </div>
              ) : (
                notes
                  .filter((note) => selectedDocIds.includes(note.documentId))
                  .map((note) => (
                    <div
                      key={note.id}
                      className="border border-zinc-150 dark:border-zinc-850 rounded-xl p-4 bg-white dark:bg-zinc-950 flex flex-col space-y-3 shadow-sm animate-in fade-in duration-200"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className="inline-block px-1.5 py-0.5 rounded text-[8px] font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-550">
                            Page {note.pageNumber}
                          </span>
                          <h5 className="text-[10px] font-bold text-zinc-900 dark:text-zinc-100 truncate mt-1">
                            {note.documentTitle}
                          </h5>
                        </div>
                        <button
                          onClick={() => deleteNote(note.id)}
                          className="text-zinc-400 hover:text-red-500 p-1 hover:bg-red-50 dark:hover:bg-red-950/20 rounded transition-colors cursor-pointer"
                          aria-label="Delete note"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>

                      {/* Cited grounding text quote */}
                      <p className="text-[10px] text-zinc-500 bg-zinc-50/50 dark:bg-zinc-900/30 p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-900/20 italic line-clamp-3">
                        "{note.snippet}"
                      </p>

                      {/* Live textarea editor */}
                      <div className="space-y-1">
                        <textarea
                          value={note.note}
                          onChange={(e) => updateNote(note.id, e.target.value)}
                          placeholder="Add custom annotations or remarks..."
                          className="w-full resize-none bg-zinc-50/20 dark:bg-zinc-900/10 border border-zinc-200 dark:border-zinc-850 rounded-lg p-2 text-[10px] outline-none focus:border-zinc-400 min-h-[50px] leading-normal"
                        />
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Slide-over PDF viewer panel */}
      <PDFViewerDrawer
        isOpen={activePDF !== null}
        onClose={() => setActivePDF(null)}
        documentId={activePDF?.documentId || ""}
        documentTitle={activePDF?.documentTitle || ""}
        pageNumber={activePDF?.pageNumber || 1}
        snippet={activePDF?.snippet || ""}
      />
    </div>
  );
}
