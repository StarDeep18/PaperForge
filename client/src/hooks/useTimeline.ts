export interface TimelineEvent {
  id: string;
  type: "upload" | "insight_save" | "ask_question" | "export_notes";
  message: string;
  timestamp: string;
}

export const getTimelineEvents = (): TimelineEvent[] => {
  try {
    const stored = localStorage.getItem("paperforge_research_timeline");
    return stored ? JSON.parse(stored) : [];
  } catch (e) {
    console.error("Failed to load timeline events", e);
    return [];
  }
};

export const addTimelineEvent = (
  type: "upload" | "insight_save" | "ask_question" | "export_notes",
  message: string
) => {
  try {
    const events = getTimelineEvents();
    const newEvent: TimelineEvent = {
      id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 11),
      type,
      message,
      timestamp: new Date().toISOString(),
    };
    const updated = [newEvent, ...events].slice(0, 50); // Keep last 50 events
    localStorage.setItem("paperforge_research_timeline", JSON.stringify(updated));
    // Dispatch custom event to trigger reactive reload in dashboard
    window.dispatchEvent(new Event("paperforge-timeline-updated"));
  } catch (e) {
    console.error("Failed to add timeline event", e);
  }
};
