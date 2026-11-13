# Fiscal Agent

![CI](https://github.com/rodrigobaruffi-byte/fiscal-agent/actions/workflows/ci.yml/badge.svg)

Brazilian fiscal invoice (NF-e) API with tax rule validation — the foundation of an AI agent for tax compliance


## Features

CRUD on Fiscal Invoices
Validates several Brazilian fiscal rules
Lists, Reports
Front in React


## Stack
Python + FastAPI
PostgreSQL 16
React
TypeScript
Docker for Postgree and API
GitHub Actions for Testing


## How to Run
Docker: docker compose up -d --build
API Address: http://127.0.0.1:8000/docs
Front: npm install + npm run dev


## Testing
.\.venv\Scripts\activate
pytest -q
node --test src/notas.test.ts
npx tsc


## Next Steps
LLM Extraction, RAG on fiscal rules, Human agents approval, quality checks,

