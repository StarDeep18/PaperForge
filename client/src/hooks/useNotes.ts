import { create } from "zustand";
import { ResearchNote } from "../types";

interface NotesState {
  notes: ResearchNote[];
  addNote: (note: Omit<ResearchNote, "id" | "createdAt">) => void;
  updateNote: (id: string, noteText: string) => void;
  deleteNote: (id: string) => void;
  exportNotes: () => void;
}

export const useNotes = create<NotesState>((set, get) => {
  // Load initial notes from localStorage
  const getInitialNotes = (): ResearchNote[] => {
    try {
      const stored = localStorage.getItem("paperforge_research_notes");
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.error("Failed to load notes from localStorage", e);
      return [];
    }
  };

  const saveNotes = (notes: ResearchNote[]) => {
    try {
      localStorage.setItem("paperforge_research_notes", JSON.stringify(notes));
    } catch (e) {
      console.error("Failed to save notes to localStorage", e);
    }
  };

  return {
    notes: getInitialNotes(),

    addNote: (noteData) => {
      const newNote: ResearchNote = {
        ...noteData,
        id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 11),
        createdAt: new Date().toISOString(),
      };
      const updatedNotes = [newNote, ...get().notes];
      set({ notes: updatedNotes });
      saveNotes(updatedNotes);
    },

    updateNote: (id, noteText) => {
      const updatedNotes = get().notes.map((note) =>
        note.id === id ? { ...note, note: noteText } : note
      );
      set({ notes: updatedNotes });
      saveNotes(updatedNotes);
    },

    deleteNote: (id) => {
      const updatedNotes = get().notes.filter((note) => note.id !== id);
      set({ notes: updatedNotes });
      saveNotes(updatedNotes);
    },

    exportNotes: () => {
      const notes = get().notes;
      if (notes.length === 0) return;

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
