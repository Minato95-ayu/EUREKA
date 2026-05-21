import puppeteer, { type Browser } from "puppeteer";
import type { Paper } from "../../types.js";

export abstract class BaseScraper {
  protected browser: Browser | null = null;

  async initialize(): Promise<void> {
    if (this.browser) return;

    this.browser = await puppeteer.launch({
      headless: process.env.PUPPETEER_HEADLESS !== "false",
      args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });
  }

  abstract searchPapers(query: string, maxResults?: number): Promise<Paper[]>;

  async cleanup(): Promise<void> {
    if (!this.browser) return;
    await this.browser.close();
    this.browser = null;
  }
}
