---
name: Product Research Tool MVP
overview: Build a B2C software product research tool that lets users explore markets, find competitors, and get structured competitive intelligence — starting with Product Identifier (B1) and Competitor Finder (B2) modules, deployed on Railway with a FastAPI backend and Next.js frontend.
todos:
  - id: setup-monorepo
    content: Set up monorepo with frontend/ (Next.js) and backend/ (FastAPI), Dockerfiles, railway.toml
    status: pending
  - id: setup-backend-foundation
    content: FastAPI app with config, Supabase client, litellm wrapper, health check endpoint
    status: pending
  - id: setup-frontend-foundation
    content: Next.js app with App Router, API client, base layout, homepage with prompt input
    status: pending
  - id: build-search-module
    content: "Search module: Google Custom Search API + DuckDuckGo fallback"
    status: pending
  - id: build-scraper-module
    content: "Scraper module: Jina Reader API + BeautifulSoup/httpx fallback"
    status: pending
  - id: build-llm-module
    content: "LLM module: litellm wrapper with Gemini, prompt templates for product identification and competitor analysis"
    status: pending
  - id: build-b1-product-identifier
    content: "B1 module: /api/identify endpoint — resolve user input to product profile or category options"
    status: pending
  - id: build-b2-competitor-finder
    content: "B2 module: /api/competitors endpoint — find competitors, return selectable list"
    status: pending
  - id: build-explore-endpoint
    content: "Explore endpoint: /api/explore — deep profile for selected competitors (features, pricing, strengths, weaknesses)"
    status: pending
  - id: build-frontend-flow
    content: "Frontend: prompt input, category selector (cards), competitor list (checkboxes), product profile display"
    status: pending
  - id: build-journey-persistence
    content: "Journey system: save/load exploration paths, Supabase schema, journey steps"
    status: pending
  - id: deploy-railway
    content: Deploy both services to Railway, configure env vars, test end-to-end
    status: pending
isProject: false
---

