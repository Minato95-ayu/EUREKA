# EUREKA Automation Layer

## Purpose

The automation layer turns EUREKA from an interactive lab into an autonomous research platform. It can search research sources, collect papers, queue experiments, run simulations through the EUREKA backend, ask ARIA for interpretation, and compile reports.

The implementation lives in `eureka-automation/`.

## Current Implementation

The first scaffold includes:

- Node.js + TypeScript project setup.
- Puppeteer base scraper.
- ArXiv scraper.
- PubMed scraper through official NCBI APIs.
- BullMQ queue processor for batch experiments.
- Redis-backed worker pool.
- EUREKA API client for current backend simulation and ARIA endpoints.
- Simple research report compiler.
- `.env.example` for local setup.

## Target Workflow

```text
Research query
-> scrape papers
-> dedupe/filter papers
-> queue experiments
-> run simulations through EUREKA backend
-> ask ARIA for analysis
-> compile insights/report
```

## Design Notes

Use official APIs first wherever possible. ArXiv and PubMed are good initial sources. Google Scholar, IEEE Xplore, Nature, and Science should be integrated carefully because automated scraping may be blocked, unreliable, or restricted by terms of service. Future integrations should prefer official APIs, exported metadata, institutional access, or user-provided credentials.

## Automation Roadmap

### Phase 1: Research Collection

- [x] Create automation module scaffold.
- [x] Add ArXiv search scraper.
- [x] Add PubMed search client.
- [ ] Add PDF download pipeline.
- [ ] Add PDF text extraction.
- [ ] Add relevance scoring and duplicate detection improvements.

### Phase 2: Batch Experiments

- [x] Add BullMQ queue and Redis worker pool.
- [x] Add current EUREKA API client.
- [ ] Add queue progress API or dashboard.
- [ ] Add checkpoint/resume records.
- [ ] Add failure audit logs.

### Phase 3: ARIA Analysis

- [x] Add basic ARIA analysis call.
- [ ] Add structured analysis prompts.
- [ ] Add insight ranking.
- [ ] Add experiment recommendation generation.
- [ ] Add final Markdown/PDF report generation.

### Phase 4: Monitoring and Notifications

- [ ] Add scheduled monitoring jobs.
- [ ] Add email notifications.
- [ ] Add Slack/Discord webhook notifications.
- [ ] Add dashboard updates through WebSocket.

### Phase 5: Advanced Research Intelligence

- [ ] Add citation graph analysis.
- [ ] Add formula and methodology extraction.
- [ ] Add paper reproducibility workflow.
- [ ] Add meta-analysis pipeline.

## Local Development

```bash
cd eureka-automation
npm install
copy .env.example .env
npm run dev -- "quantum computing"
```

Redis and the EUREKA backend should be running before executing batch workflows.
