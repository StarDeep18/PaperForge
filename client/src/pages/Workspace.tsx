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

export default function Workspace() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string; citations?: Citation[]; confidence?: string; evidence?: any[] }>>([]);
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);

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

  // Scroll to active citation card and highlight it
  const handleCitationClick = (citationNum: string) => {
    setActiveCitationId(citationNum);
    const element = citationRefs.current[citationNum];
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "nearest" });
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

      {/* ── RIGHT COLUMN: Evidence & Grounding citations ─────────── */}
      <div className="col-span-3 border-l border-zinc-200 dark:border-zinc-800 flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-950">
        
        {/* Upper Pane: EvidenceStatements Log */}
        <div className="flex-1 flex flex-col h-1/2 min-h-0 border-b border-zinc-200 dark:border-zinc-800 p-4">
          <span className="text-xs font-bold text-zinc-900 dark:text-zinc-50 uppercase tracking-wider flex items-center gap-1.5 mb-3.5">
            <Sparkles className="h-4 w-4 text-zinc-500" />
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
            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-50 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-zinc-500" />
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
    </div>
  );
}
