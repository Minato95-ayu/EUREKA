import type { AutomationReport, Paper } from "../types.js";

export class ReportCompiler {
  compileResearchReport(query: string, papers: Paper[], queuedExperimentCount: number): AutomationReport {
    const topTitles = papers.slice(0, 5).map((paper) => paper.title).filter(Boolean);

    return {
      query,
      generatedAt: new Date().toISOString(),
      paperCount: papers.length,
      queuedExperimentCount,
      insights: [
        `Found ${papers.length} papers for "${query}".`,
        `Queued ${queuedExperimentCount} experiments for ARIA-assisted analysis.`,
        topTitles.length > 0 ? `Top papers: ${topTitles.join("; ")}` : "No paper titles were available."
      ]
    };
  }
}
