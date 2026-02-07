# PartSelect Chat Agent

An AI-powered chat assistant for PartSelect.com, built as a Chrome Extension side panel. The agent helps customers find, troubleshoot, and get installation guidance for **refrigerator** and **dishwasher** replacement parts.

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  Chrome Extension       │  HTTP   │  Python FastAPI Backend       │
│  (React Side Panel)     │ ──────> │                              │
│                         │         │  POST /api/chat              │
│  - ChatWindow UI        │         │  ┌────────────────────────┐  │
│  - Part cards           │         │  │ Guardrails (topic gate) │  │
│  - Suggested queries    │         │  └──────────┬─────────────┘  │
│  - Typing indicator     │         │  ┌──────────▼─────────────┐  │
│  - Conversation history │         │  │ Intent Detection       │  │
│                         │         │  │ Entity Extraction      │  │
└─────────────────────────┘         │  └──────────┬─────────────┘  │
                                    │  ┌──────────▼─────────────┐  │
                                    │  │ Vector Search (ChromaDB)│  │
                                    │  │ + Metadata Filtering   │  │
                                    │  └──────────┬─────────────┘  │
                                    │  ┌──────────▼─────────────┐  │
                                    │  │ GPT-4 Response Gen     │  │
                                    │  └────────────────────────┘  │
                                    └──────────────────────────────┘
                                                 │
                                    ┌──────────────────────────────┐
                                    │  Data Pipeline (offline)     │
                                    │  Playwright Scraper           │
                                    │  → PartSelect.com            │
                                    │  → Chunk + Embed (OpenAI)    │
                                    │  → Store in ChromaDB         │
                                    └──────────────────────────────┘
```

## High-Level Components

### Frontend (React + Chrome Extension)
- **ChatWindow** — Main chat interface with message bubbles, markdown rendering, and auto-scroll
- **Part Cards** — Rich product cards displayed inline with images, prices, PS numbers, and direct links to PartSelect.com
- **Suggested Queries** — Contextual follow-up buttons that appear after each assistant response
- **Typing Indicator** — Animated dots shown while waiting for backend response
- **Conversation History** — Full chat history sent with each request for multi-turn context

### Backend (Python FastAPI)
- **RAG Pipeline** — Retrieval-Augmented Generation: embeds user query, searches ChromaDB for relevant parts data, passes context to GPT-4
- **Guardrails** — Two-tier topic filtering (fast keyword check + LLM fallback) to keep the agent focused on refrigerator/dishwasher parts only
- **Intent Detection** — Classifies queries into: PART_LOOKUP, COMPATIBILITY_CHECK, INSTALLATION_HELP, TROUBLESHOOT, or GENERAL
- **Entity Extraction** — Extracts PS part numbers and model numbers from user messages using regex
- **Metadata-Filtered Search** — Uses detected intent to apply ChromaDB metadata filters (e.g., only search compatibility chunks for compatibility questions)
- **System Prompt** — Enforces PartSelect assistant persona, response format, and accuracy constraints

### Data Pipeline
- **Playwright Scraper** — Browser-based scraper (PartSelect blocks non-browser requests) that collects part data from category and product pages
- **Chunking** — Each part produces multiple chunks: overview, compatibility, installation, and troubleshooting
- **Embedding + Indexing** — Chunks are embedded with OpenAI `text-embedding-3-small` and stored in ChromaDB with metadata for filtered retrieval

## File Structure

```
case-study-main/
├── public/
│   ├── index.html                    # HTML template
│   └── manifest.json                 # Chrome Extension manifest v3
├── src/
│   ├── api/
│   │   └── api.js                    # Frontend → Backend API calls
│   ├── components/
│   │   ├── ChatWindow.js             # Main chat UI component
│   │   └── ChatWindow.css            # Chat styles, part cards, typing indicator
│   ├── App.js                        # App shell with branded header
│   ├── App.css                       # Global styles and header
│   └── index.js                      # React entry point
├── backend/
│   ├── main.py                       # FastAPI app with CORS
│   ├── config.py                     # Settings from .env
│   ├── .env                          # Environment variables (API keys)
│   ├── .env.example                  # Template for .env
│   ├── requirements.txt              # Python dependencies
│   ├── models/
│   │   └── schemas.py                # Pydantic request/response models
│   ├── routers/
│   │   └── chat.py                   # POST /api/chat endpoint
│   ├── services/
│   │   ├── rag_service.py            # Core RAG pipeline orchestration
│   │   ├── embedding_service.py      # OpenAI embeddings wrapper
│   │   ├── llm_service.py            # GPT-4 chat wrapper
│   │   ├── vector_store.py           # ChromaDB operations
│   │   └── guardrails.py             # Topic filtering and off-topic responses
│   ├── prompts/
│   │   └── system_prompt.py          # System prompt and topic classifier
│   ├── scraper/
│   │   └── spider.py                 # Playwright-based PartSelect scraper
│   ├── indexer/
│   │   └── build_index.py            # Chunk, embed, and index into ChromaDB
│   └── data/
│       ├── parts.jsonl               # Scraped parts data (generated)
│       └── chroma_db/                # ChromaDB persistent storage (generated)
├── package.json                      # Frontend dependencies
├── Frontend.md                       # Original CRA readme
└── README.md                         # This file
```

## Prerequisites

- **Node.js** >= 16
- **Python** >= 3.10
- **OpenAI API Key** with access to GPT-4 and embeddings

## Setup & Execution

### 1. Install Frontend Dependencies

```bash
cd case-study-main
npm install
```

### 2. Set Up the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and set your OpenAI API key:
# OPENAI_API_KEY=sk-your-actual-key-here
```

### 4. Scrape PartSelect Data (first time only)

```bash
source venv/bin/activate
playwright install chromium
python -m scraper.spider
```

This crawls PartSelect.com for refrigerator and dishwasher parts. Output goes to `data/parts.jsonl`. Takes approximately 1-3 hours depending on the number of parts scraped.

### 5. Build the Search Index (after scraping)

```bash
python -m indexer.build_index
```

Chunks the scraped data, generates embeddings via OpenAI, and stores everything in ChromaDB at `data/chroma_db/`.

### 6. Start the Backend Server

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Verify with:
```bash
curl http://localhost:8000/health
```

### 7. Start the Frontend (Development)

```bash
cd case-study-main
npm start
```

Opens at `http://localhost:3000`.

### 8. Load as Chrome Extension

```bash
npm run build
```

1. Open `chrome://extensions/` in Chrome
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `build/` folder
4. The PartSelect Assistant will appear as a side panel

## Example Queries

- "How can I install part number PS11752778?"
- "Is this part compatible with my WDT780SAEM1 model?"
- "The ice maker on my Whirlpool fridge is not working. How can I fix it?"
- "My dishwasher is not draining, what part do I need?"
- "Find parts for my GE refrigerator"

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **ChromaDB** (local) over Pinecone | Zero infrastructure, no external API keys, runs locally. Easily swappable for production via the VectorStore abstraction. |
| **Regex-based intent detection** over LLM classification | Instant (0ms) vs 500ms+ per query. The four intents (lookup, compatibility, install, troubleshoot) are reliably detectable with keyword matching. |
| **Playwright** over requests for scraping | PartSelect returns 403 for non-browser requests. Playwright renders JavaScript and passes bot detection. |
| **Structured API response** (content + parts[] + suggested_queries[]) | Enables rich UI rendering (clickable product cards, action buttons) instead of plain text. |
| **Stateless backend** with conversation history sent per request | Simpler, more scalable. No server-side session management needed. |
| **Two-tier guardrails** (keyword check → LLM fallback) | Fast path for obvious on/off-topic queries; LLM only called for ambiguous cases. |

## Extensibility

- **Add appliance types**: Add category URLs to the scraper, update guardrails keywords, expand the system prompt
- **Scale to full catalog**: Swap ChromaDB for Pinecone/Qdrant (one-file change in `vector_store.py`)
- **Streaming responses**: FastAPI supports SSE, OpenAI supports `stream=True` — can be added to the `/api/chat` endpoint
- **Page context awareness**: The Chrome Extension can detect which PartSelect product page the user is viewing and auto-include that context
- **Response caching**: Add a cache keyed on (query_hash, top_chunk_ids) to reduce redundant GPT-4 calls
