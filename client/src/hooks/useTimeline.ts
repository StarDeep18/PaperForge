import { create } from "zustand";
import { api } from "../services/api";

export interface TimelineEvent {
  id: string;
  type: "upload" | "insight_save" | "ask_question" | "export_notes";
  message: string;
  timestamp: string;
}

interface TimelineState {
  events: TimelineEvent[];
  fetchEvents: () => Promise<void>;
  addEvent: (type: TimelineEvent["type"], message: string) => Promise<void>;
}

export const useTimeline = create<TimelineState>((set, get) => ({
  events: [],
  
  fetchEvents: async () => {
    try {
      const response = await api.get<any[]>("/timeline");
      const mapped = response.data.map(e => ({
        id: e.id,
        type: e.type,
        message: e.message,
        timestamp: e.timestamp,
      }));
      set({ events: mapped });
    } catch (e) {
      console.error("Failed to fetch timeline events from backend:", e);
    }
  },

  addEvent: async (type, message) => {
    try {
      const response = await api.post("/timeline", { type, message });
      const created = response.data;
      const mapped: TimelineEvent = {
        id: created.id,
        type: created.type,
        message: created.message,
        timestamp: created.timestamp,
      };
      set({ events: [mapped, ...get().events].slice(0, 50) });
      // Notify active dashboard
      window.dispatchEvent(new Event("paperforge-timeline-updated"));
    } catch (e) {
      console.error("Failed to push timeline event to backend:", e);
    }
  }
}));

// Legacy synchronous wrappers for seamless backward compatibility
export const getTimelineEvents = (): TimelineEvent[] => {
  return useTimeline.getState().events;
};

export const addTimelineEvent = (
  type: TimelineEvent["type"],
  message: string
) => {
  // Execute asynchronously
  useTimeline.getState().addEvent(type, message);
};
