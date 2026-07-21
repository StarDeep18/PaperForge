import { create } from "zustand";
import { ResearchNote } from "../types";
import { addTimelineEvent } from "./useTimeline";
import { api } from "../services/api";

interface NotesState {
  notes: ResearchNote[];
  fetchNotes: () => Promise<void>;
  addNote: (note: Omit<ResearchNote, "id" | "createdAt">) => Promise<void>;
  updateNote: (id: string, noteText: string) => Promise<void>;
  deleteNote: (id: string) => Promise<void>;
  exportNotes: () => void;
}

export const useNotes = create<NotesState>((set, get) => {
  return {
    notes: [],

    fetchNotes: async () => {
      try {
        const response = await api.get<any[]>("/notes");
        const mapped = response.data.map((n) => ({
          id: n.id,
          documentId: n.document_id,
          documentTitle: n.document_title,
          pageNumber: n.page_number,
          snippet: n.snippet,
          note: n.note || "",
          createdAt: n.created_at || n.createdAt,
        }));
        set({ notes: mapped });
      } catch (e) {
        console.error("Failed to load notes from backend API:", e);
      }
    },

    addNote: async (noteData) => {
      try {
        const response = await api.post("/notes", {
          document_id: noteData.documentId,
          document_title: noteData.documentTitle,
          page_number: noteData.pageNumber,
          snippet: noteData.snippet,
          note: noteData.note,
        });
        const saved = response.data;
        const mapped: ResearchNote = {
          id: saved.id,
          documentId: saved.document_id,
          documentTitle: saved.document_title,
          pageNumber: saved.page_number,
          snippet: saved.snippet,
          note: saved.note || "",
          createdAt: saved.created_at || saved.createdAt,
        };
        set({ notes: [mapped, ...get().notes] });
      } catch (e) {
        console.error("Failed to save note to backend API:", e);
      }
    },

    updateNote: async (id, noteText) => {
      // Optimistic update
      const updatedNotes = get().notes.map((note) =>
        note.id === id ? { ...note, note: noteText } : note
      );
      set({ notes: updatedNotes });

      try {
        await api.patch(`/notes/${id}`, { note: noteText });
      } catch (e) {
        console.error("Failed to update note in backend API:", e);
      }
    },

    deleteNote: async (id) => {
      // Optimistic delete
      const updatedNotes = get().notes.filter((note) => note.id !== id);
      set({ notes: updatedNotes });

      try {
        await api.delete(`/notes/${id}`);
      } catch (e) {
        console.error("Failed to delete note in backend API:", e);
      }
    },

    exportNotes: () => {
      const notes = get().notes;
      if (notes.length === 0) return;

      addTimelineEvent("export_notes", `Exported ${notes.length} research notes`);

      let markdown = `# PaperForge Research Notes\n\n`;
      markdown += `Exported on: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}\n\n`;
      markdown += `---\n\n`;

      notes.forEach((note, idx) => {
        markdown += `### Note ${idx + 1}: ${note.documentTitle} (Page ${note.pageNumber})\n\n`;
        markdown += `> **Cited Grounding Passage:**\n`;
        markdown += `> ${note.snippet.replace(/\n/g, "\n> ")}\n\n`;
        markdown += `**My Research Thoughts & Annotations:**\n`;
        markdown += `${note.note || "_No custom thoughts added._"}\n\n`;
        markdown += `*Saved on: ${new Date(note.createdAt).toLocaleString()}*\n\n`;
        markdown += `---\n\n`;
      });

      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `paperforge_research_notes_${new Date().toISOString().split("T")[0]}.md`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
  };
});
