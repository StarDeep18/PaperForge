import { api } from "./api";
import { Document, PaginatedDocumentResponse, UploadResponse } from "../types";

export const documentService = {
  /**
   * Fetches a paginated list of documents.
   */
  async listDocuments(
    page = 1,
    size = 20,
    collectionId?: string
  ): Promise<PaginatedDocumentResponse> {
    const params: Record<string, any> = { page, size };
    if (collectionId) {
      params.collection_id = collectionId;
    }
    const response = await api.get<PaginatedDocumentResponse>("/documents", {
      params,
    });
    return response.data;
  },

  /**
   * Uploads one or multiple files.
   */
  async uploadDocuments(
    files: File[],
    collectionId?: string
  ): Promise<UploadResponse[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    if (collectionId) {
      formData.append("collection_id", collectionId);
    }

    const response = await api.post<UploadResponse[]>("/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /**
   * Deletes a single document.
   */
  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  },

  /**
   * Retrieves single document metadata details.
   */
  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
  },
};
