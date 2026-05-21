export type PaperSource = "arxiv" | "pubmed" | "scholar" | "ieee" | "publisher";

export interface Paper {
  id: string;
  source: PaperSource;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  pdfUrl?: string;
  publishedDate?: string;
  keywords?: string[];
  relevanceScore?: number;
}

export interface ExperimentJob {
  experimentId: string;
  name: string;
  type: string;
  parameters: Record<string, unknown>;
  priority: number;
}

export interface AutomationReport {
  query: string;
  generatedAt: string;
  paperCount: number;
  queuedExperimentCount: number;
  insights: string[];
}
