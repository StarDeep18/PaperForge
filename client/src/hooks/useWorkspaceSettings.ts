import { create } from "zustand";
import { api } from "../services/api";

export interface WorkspaceSettings {
  theme: string;
  selected_document_ids: string[];
  active_document_id: string;
  active_conversation_id: string;
}

interface WorkspaceSettingsState {
  settings: WorkspaceSettings;
  loading: boolean;
  fetchSettings: () => Promise<void>;
  updateSettings: (updates: Partial<WorkspaceSettings>) => Promise<void>;
}

export const useWorkspaceSettings = create<WorkspaceSettingsState>((set, get) => ({
  settings: {
    theme: "dark", // Default to dark for premium aesthetics
    selected_document_ids: [],
    active_document_id: "",
    active_conversation_id: "",
  },
  loading: true,

  fetchSettings: async () => {
    try {
      const response = await api.get<WorkspaceSettings>("/workspaces/settings");
      set({ settings: response.data, loading: false });
      
      // Update DOM theme indicator
      if (typeof window !== "undefined") {
        const root = window.document.documentElement;
        root.classList.remove("light", "dark");
        root.classList.add(response.data.theme || "dark");
      }
    } catch (e) {
      console.error("Failed to fetch workspace settings from backend:", e);
      set({ loading: false });
    }
  },

  updateSettings: async (updates) => {
    const nextSettings = { ...get().settings, ...updates };
    set({ settings: nextSettings });

    if (updates.theme && typeof window !== "undefined") {
      const root = window.document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(updates.theme);
    }

    try {
      await api.put("/workspaces/settings", nextSettings);
    } catch (e) {
      console.error("Failed to update workspace settings in backend:", e);
    }
  }
}));
export type { WorkspaceSettingsState };
