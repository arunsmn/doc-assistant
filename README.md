# DocMind — Intelligent Document Assistant

A production-grade RAG (Retrieval-Augmented Generation) system that answers questions from your documents with source citations, conversational memory, and an intelligent agent layer that decides _how_ to answer before it answers.

**Live demo:** `https://doc-assistant-three.vercel.app/` &nbsp;|&nbsp; **Backend API docs:** `https://doc-assistant-backend-ug4u.onrender.com`

---

## What makes this different from a basic RAG demo

Most RAG projects chunk a PDF, throw it at an LLM, and call it done. This system is built with production concerns in mind:

| Feature                     | Why it matters                                                                                                                                                              |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Agent query routing**     | Classifies every question as document-based, general knowledge, or irrelevant — and routes accordingly. No wasted API calls, no hallucinated answers from the wrong source. |
| **Table-aware extraction**  | Uses `pdfplumber` instead of naive text extraction. Tables are converted to readable key-value pairs so structured data is actually retrievable.                            |
| **Conversational memory**   | Follow-up questions work. "What about the pricing?" correctly references the previous answer without re-asking the full question.                                           |
| **LLM-as-judge evaluation** | A scored test suite measures accuracy, hallucination rate, and routing correctness. The system can prove how well it works.                                                 |
| **Per-document isolation**  | Each uploaded document gets its own Chroma collection. Asking about Doc A never pulls chunks from Doc B.                                                                    |
| **Source citations**        | Every RAG answer includes the exact pages and text snippets it was generated from. Users can verify answers.                                                                |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│         Chat UI · Document Uploader · Source Cards       │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (REST)
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────┐    │
│  │   Routes    │    │        Agent Layer            │    │
│  │  /upload    │    │                              │    │
│  │  /chat      ├───►│  Query Router (Gemini)        │    │
│  │  /evaluate  │    │  rag │ llm │ reject           │    │
│  └─────────────┘    └──────┬───────────────────────┘    │
│                            │                             │
│              ┌─────────────▼─────────────┐              │
│              │       RAG Pipeline         │              │
│              │                           │              │
│              │  pdfplumber → chunks       │              │
│              │  sentence-transformers     │              │
│              │  Chroma vector store       │              │
│              │  Gemini 1.5 Flash          │              │
│              └───────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### Query flow

```
User question
      │
      ▼
Agent Router (Gemini, temp=0)
      │
      ├── "rag"    → embed question → Chroma search → top-5 chunks
      │             → history-aware retriever (rephrases follow-ups)
      │             → Gemini generates grounded answer + source pages
      │
      ├── "llm"    → Gemini answers directly from training knowledge
      │
      └── "reject" → polite decline, no LLM call made
```

---

## Tech stack

| Layer            | Technology                                 | Why                                   |
| ---------------- | ------------------------------------------ | ------------------------------------- |
| LLM              | Google Gemini 1.5 Flash                    | Fast, capable, generous free tier     |
| Embeddings       | `sentence-transformers` (all-MiniLM-L6-v2) | Free, local, no API calls needed      |
| Vector DB        | ChromaDB                                   | Simple, persistent, production-ready  |
| Orchestration    | LangChain 0.3                              | LCEL chains, history-aware retrieval  |
| PDF extraction   | pdfplumber                                 | Handles tables and structured content |
| Backend          | FastAPI + Python 3.13                      | Async, auto-docs, production standard |
| Frontend         | React + Vite                               | Fast, modern, component-based         |
| Containerisation | Docker + docker-compose                    | One-command local setup               |
| CI/CD            | GitHub Actions                             | Auto-test and deploy on every push    |
| Backend hosting  | Render                                     | Free tier, persistent disk for Chroma |
| Frontend hosting | Vercel                                     | Global CDN, zero-config React deploys |

---

## Getting started

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/yourusername/doc-assistant
cd doc-assistant

# Add your Gemini API key
echo "GOOGLE_API_KEY=your_key_here" > backend/.env

docker-compose up --build
```

Open `http://localhost:5173`. Done.

### Option 2 — Manual setup

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

echo "GOOGLE_API_KEY=your_key_here" > .env
uvicorn app.main:app --reload --port 8000
```

**Frontend** (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## Project structure

```
doc-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, route registration
│   │   ├── config.py            # Pydantic settings — all config in one place
│   │   ├── routes/
│   │   │   ├── chat.py          # POST /chat — routes query, returns answer
│   │   │   └── documents.py     # POST /upload, POST /evaluate
│   │   ├── services/
│   │   │   ├── ingestion.py     # pdfplumber → chunks → embeddings → Chroma
│   │   │   └── retriever.py     # history-aware retrieval → Gemini → answer
│   │   ├── agents/
│   │   │   └── router.py        # classifies queries: rag / llm / reject
│   │   └── evals/
│   │       ├── scorer.py        # LLM-as-judge evaluation pipeline
│   │       └── test_questions.json  # golden Q&A test set
│   ├── tests/
│   │   └── test_ingestion.py    # pytest unit tests (run in CI)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # axios instance, all API calls
│   │   ├── hooks/useChat.js     # all state and business logic
│   │   └── components/
│   │       ├── Sidebar.jsx      # document list + upload zone
│   │       ├── ChatArea.jsx     # message history + auto-scroll
│   │       ├── Message.jsx      # bubble + route badge + timestamps
│   │       ├── SourceCards.jsx  # page citations with snippets
│   │       ├── ChatInput.jsx    # textarea + send button
│   │       └── TypingIndicator.jsx
│   ├── Dockerfile
│   └── vercel.json
├── .github/
│   └── workflows/
│       └── ci.yml               # test → deploy backend → deploy frontend
├── docker-compose.yml
└── README.md
```

---

## Evaluation

The system includes a built-in evaluation pipeline that scores answer quality using an LLM-as-judge approach — a standard technique used in production RAG systems.

```bash
# After uploading a document, run evaluation against it
POST /documents/evaluate/{collection_name}
```

Each question is scored 0–2:

- **2** — correct, captures key information
- **1** — partial, related but missing details
- **0** — incorrect or hallucinated

Metrics reported:

- Overall accuracy (%)
- Routing accuracy (%)
- Perfect / partial / incorrect answer counts
- Hallucination count
- Per-category breakdown (factual, summary, general, reject)

---

## CI/CD pipeline

Every push to `main` triggers three sequential GitHub Actions jobs:

```
push to main
      │
      ▼
[1] Run tests (pytest)
      │ pass
      ▼
[2] Deploy backend → Render
[3] Deploy frontend → Vercel  (parallel)
```

If tests fail, deployment is blocked automatically.

---

## Chunking and retrieval configuration

All tunable parameters live in `backend/app/config.py`:

```python
chunk_size: int = 500       # characters per chunk
chunk_overlap: int = 50     # overlap between chunks
top_k: int = 5              # chunks retrieved per query
gemini_model: str = "gemini-1.5-flash"
```

Experiment with these to observe the accuracy tradeoffs:

- Smaller chunks → more precise retrieval, less context per chunk
- Larger `top_k` → more context, noisier results
- More overlap → fewer split concepts, larger index

---

## Environment variables

```env
# backend/.env
GOOGLE_API_KEY=your_gemini_api_key_here
```

```env
# frontend/.env.production
VITE_API_URL=https://your-backend.onrender.com
```

---

## Future improvements

- [ ] OCR support for scanned / image-based PDFs
- [ ] DOCX and TXT file support
- [ ] Streaming responses for faster perceived latency
- [ ] Hybrid search (BM25 + semantic) for better retrieval
- [ ] User authentication and document management
- [ ] Evaluation dashboard in the React UI

---

## Key concepts demonstrated

**RAG (Retrieval-Augmented Generation)** — Grounds LLM answers in document content rather than training knowledge, reducing hallucination.

**Agentic routing** — An LLM classifying its own inputs to decide which tool to use. Foundational pattern in agent systems.

**LLM-as-judge** — Using a language model to evaluate another language model's output. Standard technique for production RAG evaluation.

**History-aware retrieval** — Rephrasing follow-up questions into standalone queries before retrieval, enabling coherent multi-turn conversations.

**Vector similarity search** — Converting text to high-dimensional vectors and finding nearest neighbours to retrieve semantically relevant content.

---

_Built with FastAPI · LangChain · ChromaDB · Gemini · React · Docker · GitHub Actions_
