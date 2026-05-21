# EUREKA Automation Layer

This module adds an autonomous research automation layer to EUREKA.

It is designed to:

- Search and scrape research metadata from trusted sources.
- Download and parse papers where legally and technically available.
- Queue and run many EUREKA experiments in parallel.
- Ask ARIA to analyze results and generate insights.
- Support scheduled research monitoring.

## Current Scope

This is an initial scaffold, not a complete production scraper.

Implemented foundations:

- TypeScript Node.js project.
- Puppeteer-based base scraper.
- ArXiv scraper.
- PubMed scraper using official NCBI endpoints.
- BullMQ batch experiment queue.
- EUREKA API client aligned with the current backend routes.
- ARIA analysis client.
- Scheduled monitoring entrypoint.

## Quick Start

```bash
cd eureka-automation
npm install
copy .env.example .env
npm run dev -- "quantum computing"
```

Redis must be running for batch processing. The root `docker-compose.yml` already defines a Redis service.

## Important Scraping Policy

Prefer official APIs first:

- ArXiv API/search pages for ArXiv papers.
- NCBI E-utilities for PubMed.
- Publisher APIs or exported metadata where available.

Google Scholar, IEEE Xplore, Nature, and Science may block scraping or restrict automated access. Add those integrations only with API keys, institutional access, or explicit permission.
