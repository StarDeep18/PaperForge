# PaperForge

**AI-Powered Research Workspace**

PaperForge helps researchers, students, and professionals understand, organize, compare, and synthesize research papers using Retrieval-Augmented Generation (RAG).

## Features

- 📄 **Upload & Parse** — Upload PDFs, DOCX, and text files with intelligent parsing
- 🗂️ **Collections** — Organize papers into named collections
- 💬 **Chat with Papers** — Ask questions about one or multiple papers
- 📝 **Citation-Aware Answers** — Every response includes source citations
- 🔍 **Semantic Search** — Find relevant content across your library
- 📊 **Paper Comparison** — Compare methodologies, findings, and conclusions
- 📚 **Literature Reviews** — Auto-generate literature review drafts
- 🧠 **Research Gaps** — Identify gaps and opportunities
- 📋 **Study Tools** — Generate notes, flashcards, and quizzes

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI |
| AI | LangChain, Google Gemini, Sentence Transformers |
| Vector DB | ChromaDB (swappable to Qdrant/Pinecone) |
| Database | SQLite (migratable to PostgreSQL) |
| Document Processing | PyMuPDF, python-docx |

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Google API Key (for Gemini)

### Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY

# Backend
cd server
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main

# Frontend (new terminal)
cd client
npm install
npm run dev
```

### Docker

```bash
docker-compose up --build
```

## Architecture

PaperForge follows **Clean Architecture** with four layers:

- **Presentation** — API endpoints and React UI
- **Application** — Use cases and orchestration
- **Domain** — Business entities and rules
- **Infrastructure** — Database, vector store, LLM, file storage

## License

MIT
