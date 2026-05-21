import type { Paper } from "../types.js";

export function dedupePapers(papers: Paper[]): Paper[] {
  const seen = new Set<string>();
  const deduped: Paper[] = [];

  for (const paper of papers) {
    const key = `${paper.source}:${paper.id || paper.title.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(paper);
  }

  return deduped;
}
