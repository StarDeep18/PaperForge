import { api } from "./api";
import { HealthResponse } from "../types";

export const healthService = {
  /**
   * Performs an audit on backend components health.
   */
  async checkHealth(): Promise<HealthResponse> {
    const response = await api.get<HealthResponse>("/health");
    return response.data;
  },
};
