import type { Paper } from "../../types.js";
import { BaseScraper } from "../base/BaseScraper.js";

export class ArxivScraper extends BaseScraper {
  async searchPapers(query: string, maxResults = 25): Promise<Paper[]> {
    await this.initialize();
    const page = await this.browser!.newPage();

    try {
      await page.setUserAgent("EUREKA research automation bot; contact: local-dev");
      const url = new URL("https://arxiv.org/search/");
      url.searchParams.set("query", query);
      url.searchParams.set("searchtype", "all");
      url.searchParams.set("abstracts", "show");
      url.searchParams.set("order", "-announced_date_first");
      url.searchParams.set("size", String(Math.min(maxResults, 50)));

      await page.goto(url.toString(), { waitUntil: "networkidle2", timeout: 30000 });

      const papers = await page.evaluate(() => {
        return Array.from(document.querySelectorAll(".arxiv-result")).map((el) => {
          const title = el.querySelector(".title")?.textContent?.replace(/\s+/g, " ").trim() || "";
          const authorText = el.querySelector(".authors")?.textContent?.replace("Authors:", "").trim() || "";
          const abstract = el.querySelector(".abstract-full")?.textContent?.replace("△ Less", "").replace(/\s+/g, " ").trim() || "";
          const href = el.querySelector(".list-title a")?.getAttribute("href") || "";
          const id = href.split("/").pop() || title;
          const pdfUrl = id ? `https://arxiv.org/pdf/${id}.pdf` : undefined;

          return {
            id,
            source: "arxiv",
            title,
            authors: authorText.split(",").map((author) => author.trim()).filter(Boolean),
            abstract,
            url: href,
            pdfUrl
          };
        });
      });

      return papers.slice(0, maxResults) as Paper[];
    } finally {
      await page.close();
    }
  }
}
