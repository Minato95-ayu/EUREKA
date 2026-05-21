import "dotenv/config";
import { ArxivScraper } from "./scrapers/arxiv/ArxivScraper.js";
import { PubmedScraper } from "./scrapers/pubmed/PubmedScraper.js";
import { BatchProcessor } from "./orchestrator/BatchProcessor.js";
import { ReportCompiler } from "./ai-analysis/ReportCompiler.js";
import { dedupePapers } from "./utils/dedupe.js";
import { logger } from "./utils/logger.js";

export class EurekaAutomation {
  private arxiv = new ArxivScraper();
  private pubmed = new PubmedScraper();
  private batch = new BatchProcessor();
  private reports = new ReportCompiler();

  async runResearchAnalysis(query: string): Promise<void> {
    logger.info(`Starting automated research analysis: ${query}`);

    const [arxivPapers, pubmedPapers] = await Promise.all([
      this.arxiv.searchPapers(query, 10),
      this.pubmed.searchPapers(query, 10)
    ]);

    const papers = dedupePapers([...arxivPapers, ...pubmedPapers]);

    const jobIds = await this.batch.addBatch(
      papers.map((paper) => ({
        name: paper.title || `${paper.source}:${paper.id}`,
        type: "research_analysis",
        parameters: {
          paper,
          query
        },
        priority: 5
      }))
    );

    const report = this.reports.compileResearchReport(query, papers, jobIds.length);
    logger.info(JSON.stringify(report, null, 2));
  }

  async cleanup(): Promise<void> {
    await this.arxiv.cleanup();
    await this.pubmed.cleanup();
    await this.batch.cleanup();
  }
}

async function main(): Promise<void> {
  const query = process.argv.slice(2).join(" ") || "quantum computing";
  const automation = new EurekaAutomation();

  try {
    await automation.runResearchAnalysis(query);
  } finally {
    await automation.cleanup();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    logger.error(error instanceof Error ? error.stack || error.message : String(error));
    process.exit(1);
  });
}
