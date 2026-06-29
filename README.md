# Highwatch RAG - Personal AI Assistant over Google Drive

A powerful, production-ready Retrieval-Augmented Generation (RAG) system that connects directly to your Google Drive. It fetches your documents, generates semantic embeddings, and allows you to chat with your files using advanced LLMs—acting as your personal ChatGPT for your private data.

Built as a trial assignment for the **AI Platform Engineer** role at **Highwatch AI**.

---

## 🚀 Live Demo
* **Frontend:** [https://hiighwatch-rag.vercel.app](https://hiighwatch-rag.vercel.app)
* **Backend API:** [https://hiighwatch-rag-3cdc.onrender.com](https://hiighwatch-rag-3cdc.onrender.com)

*(Note: The backend is hosted on Render's Free Tier and may take 30-60 seconds to wake up from sleep).*

---

## ✨ Core Features

### 1. Google Drive Integration (Working)
* **OAuth 2.0:** Secure user authentication using Google Cloud Console.
* **Document Fetching:** Automatically retrieves `.pdf`, `.docx`, and `.txt` files directly from the user's Drive.
* **Metadata Tracking:** Stores `file_id`, `name`, `mimeType`, and `modifiedTime` in MongoDB.

### 2. Document Processing & Chunking (Working)
* **Extraction:** Uses `PyMuPDF` (PDFs) and `python-docx` (Docs) for highly accurate text extraction.
* **Semantic Chunking:** Text is cleaned and chunked into highly optimized 250-word segments with a 50-word overlap to perfectly fit the embedding model's maximum token limit (256 tokens) without data loss.

### 3. Embedding Layer (Working)
* **Model:** Uses `SentenceTransformers` (`all-MiniLM-L6-v2`) running completely locally.
* **Batch Processing:** Processes embeddings in batches (size=4) with aggressive garbage collection to optimize memory usage and prevent OOM errors on limited hardware.

### 4. Storage Layer (Working)
* **Vector Database:** Uses **FAISS** (`IndexFlatIP` for Cosine Similarity) for lightning-fast local vector retrieval.
* **Database:** Uses **MongoDB** to persist document metadata and conversational chat history.

### 5. Query System & RAG (Working)
* **Top-K Retrieval:** Dynamically retrieves the top 15 most relevant chunks to provide massive context windows to the LLM.
* **Intelligent Routing:** Automatically detects "Summarize" requests and rewrites the semantic query while forcing FAISS to scan the *entire* database for that specific document.

### 6. AI Answer Layer (Working)
* **LLM:** Powered by **Groq** (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) for blazing-fast inference.
* **Grounded Answers:** Strictly instructed to answer *only* using the provided context. It will explicitly refuse to hallucinate if the answer is not in the synced documents.
* **Citations:** Every answer returns a list of exact source documents used to generate the response.

---

## 🧠 Business Analytics Agents ("Claws")

In addition to document Q&A, Highwatch ships an **autonomous Data / Business
Analytics Agent** layer. Upload a CSV/Excel file (or import a spreadsheet from
Google Drive) and run any of five specialised agents over it.

> **Design principle:** every number is computed **deterministically** in
> `pandas` / `numpy` / `scikit-learn`. The LLM (Groq) is used *only* to turn the
> pre-computed statistics into a readable narrative — it is explicitly forbidden
> from inventing figures. If `GROQ_API_KEY` is missing or rate-limited, each
> agent gracefully falls back to a computed-facts summary, so it never breaks.

| Claw | What it does |
|------|--------------|
| **Data Analyst** | Cleans the data, surfaces KPIs + trends + correlations, and writes a structured insight summary. |
| **KPI Monitoring** | Compares each metric period-over-period, flags significant moves, explains likely causes, recommends actions. |
| **Anomaly Detection** | Flags unusual values/exceptions using **z-score + IQR**, with timestamps and explanations. |
| **Customer Segmentation** | Clusters customers/entities with **KMeans** (auto-`k` via silhouette score) and describes each segment in business terms. |
| **Business Performance** | Orchestrates all of the above into an executive report: highlights, risks, segment insights, and prioritised next actions. |

### How it works
1. **Ingest** — CSV/XLSX/TSV upload or Google Sheets/Drive import → cleaned (whitespace, dupes, currency→numeric, date parsing) → stored as Parquet with metadata in MongoDB.
2. **Compute** — `analytics/engine.py` computes KPIs, time-series trends (with partial-bucket trimming), anomalies, period changes, and segments.
3. **Narrate** — `analytics/narrator.py` sends the computed JSON facts to Groq for a grounded, markdown insight.
4. **Visualise** — the `/analytics` dashboard renders KPI cards, sparkline trends, anomaly tables, and segment cards.

### Analytics API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/analytics/upload` | Upload a CSV/Excel dataset (multipart) |
| `GET`  | `/analytics/datasets` | List the user's datasets |
| `GET`  | `/analytics/dataset/{id}` | Dataset profile + preview |
| `DELETE` | `/analytics/dataset/{id}` | Delete a dataset |
| `GET`  | `/analytics/drive/list` | List CSV/Excel/Sheets in Drive |
| `POST` | `/analytics/drive/import?file_id=...` | Import a Drive spreadsheet |
| `GET`  | `/analytics/claws` | List available agents |
| `POST` | `/analytics/run` | Run a Claw `{ dataset_id, claw }` |

A ready-to-use demo file lives at **`sample_data/sales_sample.csv`** (540 rows of
synthetic sales data with an embedded trend + injected anomalies).

Open the dashboard and click **"Analytics Agents"** in the sidebar, or go to `/analytics`.

---

## 🛠 Tech Stack

**Backend:**
* Python 3.9+
* FastAPI (API Routing)
* FAISS (Vector Database)
* MongoDB (NoSQL Database)
* PyTorch & SentenceTransformers (Embeddings)
* **pandas / NumPy / scikit-learn (Analytics Agents)**
* Groq SDK (LLM Inference)
* Google API Client (OAuth & Drive)

**Frontend:**
* Next.js 14 (App Router)
* React & TailwindCSS
* Framer Motion (Animations)
* Lucide React (Icons)
* React Markdown (Response Formatting)

---

## ⚙️ Local Development Setup

### Prerequisites
1. Python 3.9+
2. Node.js 18+
3. A Google Cloud Console project with OAuth 2.0 Client IDs.
4. A Groq API Key.
5. A MongoDB Cluster URI.

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
touch .env
```
Add the following to `backend/.env`:
```env
ENVIRONMENT=development
PORT=8000
FRONTEND_URL=http://localhost:3000
API_URL=http://127.0.0.1:8000
MONGO_URI=your_mongodb_uri
GROQ_API_KEY=your_groq_api_key
GOOGLE_CREDENTIALS_PATH=credentials.json
```
*(Place your Google OAuth `credentials.json` in the backend root directory).*

Start the backend:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
touch .env.local
```
Add the following to `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the frontend:
```bash
npm run dev
```

---

## 📋 Evaluation Criteria Achieved

### Must Have:
✅ Google Drive integration working end-to-end.  
✅ Documents processed, cleaned, and chunked correctly.  
✅ Q&A system working flawlessly with FAISS and Groq.  

### Strong Candidate:
✅ **Good chunking strategy:** Implemented 250-word chunks (50 overlap) specifically tailored to bypass the 256-token limit of the `all-MiniLM-L6-v2` model, preventing massive data truncation.  
✅ **Relevant answers:** Context window intelligently expanded to 15 chunks (3,750 words) to ensure the LLM has maximum visibility.  
✅ **Clean API design:** Separated into `connectors/`, `processing/`, `embedding/`, `search/`, and `api/` architecture.  

### Exceptional:
✅ **Incremental sync:** The system checks `modifiedTime` from Google Drive against MongoDB and *only* downloads files that are new or updated.  
✅ **Metadata filtering:** Users can click on a source citation in the chat to instantly summarize that specific document via strict FAISS metadata filtering.  

---

## 📝 Sample Queries
Check out `SAMPLE_QUERIES.md` for examples of simple data retrieval, complex analysis, summarization, and hallucination prevention.