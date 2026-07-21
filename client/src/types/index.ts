export interface DocumentMetadata {
  title?: string;
  authors?: string[];
  abstract?: string;
  publication_date?: string;
  journal?: string;
  doi?: string;
  keywords?: string[];
  page_count: number;
  word_count: number;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  status: string;
  metadata: DocumentMetadata;
  collection_id?: string;
  chunk_count: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedDocumentResponse {
  items: Document[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
  processing_time: number;
  warnings: string[];
}

export interface Citation {
  citation_id: string;
  document_id: string;
  document_title: string;
  pages: number[];
  supporting_chunks: string[];
  confidence: string;
  formatted_reference: string;
}

export interface EvidenceNode {
  statement: string;
  supporting_chunks: string[];
  confidence: number;
}

export interface EvidenceGraph {
  nodes: EvidenceNode[];
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence: string;
  evidence_graph: EvidenceGraph;
  warnings: string[];
}

export interface ChatRequest {
  query: string;
  workspace_id?: string;
  conversation_history?: Array<{ role: "user" | "assistant"; content: string }>;
  retrieval_options?: Record<string, any>;
  generation_options?: Record<string, any>;
}

export interface HealthResponse {
  upload_service: string;
  parser: string;
  embedding_provider: string;
  vector_store: string;
  retrieval: string;
  generation: string;
  citation: string;
  overall_status: string;
}

export interface ResearchNote {
  id: string;
  documentId: string;
  documentTitle: string;
  pageNumber: number;
  snippet: string;
  note: string;
  createdAt: string;
}

