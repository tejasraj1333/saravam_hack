# ShikshaSetu 🎓

**Multilingual AI Personal Tutor** — Upload your study PDFs, ask questions in Hindi/Hinglish, listen to answers, take adaptive quizzes, and track concept mastery. Powered by [Sarvam AI](https://sarvam.ai).

---

## ✨ Features

| Feature | Description |
|---|---|
| 📚 **Document Library** | Upload PDF notes & textbooks; local PyMuPDF extraction (no API cost) |
| 🤖 **RAG Tutor** | Grounded answers from your documents with page-level citations |
| 🎙️ **Voice Input** | Record questions — transcribed via **Saaras v4** |
| 🔊 **TTS Output** | Answers read aloud via **Bulbul v4 Flash** in Hindi/regional languages |
| 🧪 **Adaptive Quiz** | LLM-generated MCQ & short-answer quizzes from your material |
| 📈 **Concept Mastery** | Transparent scoring + spaced-repetition revision plan |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Sarvam AI](https://indus.sarvam.ai) API key

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set SARVAM_API_KEY=your_key_here

# Start the server
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### 3. Run Tests

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

> All tests mock Sarvam API calls — **no credits consumed**.

---

## 🏗️ Architecture

```
backend/
  app/
    main.py          ← FastAPI app + CORS
    config.py        ← Settings (pydantic-settings)
    models.py        ← Domain models
    schemas.py       ← API schemas
    api/routes.py    ← All API endpoints
    services/
      sarvam_service.py    ← Sarvam LLM / STT / TTS wrappers
      document_service.py  ← PDF extraction + chunking (PyMuPDF)
      retrieval_service.py ← TF-IDF vector index (local, free)
      tutor_service.py     ← RAG pipeline
      speech_service.py    ← Voice I/O orchestration
      quiz_service.py      ← Quiz generation + evaluation
      mastery_service.py   ← Concept tracking + revision
    repositories/
      local_store.py  ← JSON file storage (MongoDB fallback)

frontend/src/
  pages/
    Dashboard.tsx  Library.tsx  Tutor.tsx  Quiz.tsx  Mastery.tsx
  services/api.ts  ← Typed fetch wrappers
```

---

## 🔑 Sarvam AI Models Used

| Feature | Model | Identifier |
|---|---|---|
| Chat LLM | Sarvam-105B | `sarvam-105b` |
| Speech-to-Text | Saaras v4 | `saaras:v4` |
| Text-to-Speech | Bulbul v4 Flash | `bulbul:v4-flash` |
| Translation | Sarvam Translate | via `client.text.translate` |

---

## 💰 Credit Budget

- **PDF extraction**: Free (local PyMuPDF)
- **Embeddings**: Free (local TF-IDF / scikit-learn)
- **LLM (tutor answers)**: ~1–3 credits per question
- **STT (voice input)**: Credits per second of audio
- **TTS (audio output)**: Credits per character
- **Tests**: 0 credits (all mocked)

Upload small PDFs (< 20 MB, < 200 pages) and avoid redundant calls to stay within budget.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SARVAM_API_KEY` | *(required)* | Your Sarvam AI API key |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB (falls back to local JSON) |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum PDF upload size |
| `MAX_PAGES` | `200` | Maximum PDF pages |
| `LLM_MODEL` | `sarvam-105b` | Chat model |
| `TTS_MODEL` | `bulbul:v4-flash` | TTS model |
| `STT_MODEL` | `saaras:v4` | STT model |

---

## ⚠️ Limitations

- AI-generated explanations may contain errors — always verify with original textbooks.
- Mastery scores are estimates based on quiz accuracy, not scientifically validated measures.
- Scanned (image-only) PDFs extract poorly without Sarvam Vision (disabled by default to save credits).
- MongoDB is optional; local JSON storage is not suitable for multi-user production use.
