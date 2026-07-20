import { api } from "./api";
import { ChatRequest, ChatResponse } from "../types";

export const chatService = {
  /**
   * Submits a prompt query to the RAG grounding system.
   */
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>("/chat", request);
    return response.data;
  },
};
