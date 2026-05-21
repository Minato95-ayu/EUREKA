import axios from "axios";
import type { Paper } from "../../types.js";

interface PubmedSummary {
  uid: string;
  title?: string;
  fulljournalname?: string;
  pubdate?: string;
  authors?: Array<{ name: string }>;
}

export class PubmedScraper {
  async initialize(): Promise<void> {
    return Promise.resolve();
  }

  async searchPapers(query: string, maxResults = 25): Promise<Paper[]> {
    const search = await axios.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {
      params: {
        db: "pubmed",
        retmode: "json",
        sort: "date",
        retmax: maxResults,
        term: query
      },
      timeout: 30000
    });

    const ids: string[] = search.data?.esearchresult?.idlist || [];
    if (ids.length === 0) return [];

    const summary = await axios.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", {
      params: {
        db: "pubmed",
        retmode: "json",
        id: ids.join(",")
      },
      timeout: 30000
    });

    const result = summary.data?.result || {};

    return ids.map((id) => {
      const item = result[id] as PubmedSummary | undefined;
      return {
        id,
        source: "pubmed",
        title: item?.title || "",
        authors: item?.authors?.map((author) => author.name) || [],
        abstract: "",
        url: `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
        publishedDate: item?.pubdate
      };
    });
  }

  async cleanup(): Promise<void> {
    return Promise.resolve();
  }
}
