# VeriText AI — AI Origin Checker & Interactive Sentence Humanizer (PoC)

An executive Proof-of-Concept (PoC) built with **Nuxt 3 (Frontend)** and **Python FastAPI (Backend)** that detects AI-generated content at the sentence level and provides interactive, one-click human rewrites for flagged sentences.

---

## Core Modules

1. **Forensic AI Detection Module (`backend/modules/detector.py`)**
   - Splits documents into individual sentences and evaluates each sentence's AI probability (`0–100%`).
   - Computes quantitative linguistic metrics: **Burstiness Score**, **Sentence Uniformity**, **Vocabulary Richness**, and **AI Cliché Density** (*"delve"*, *"tapestry"*, *"testament"*, *"furthermore"*, etc.).
   - Explains *why* specific sentences look AI-generated.

2. **Interactive Sentence Humanizer / Correction Module (`backend/modules/corrector.py`)**
   - Generates **3 distinct human-sounding rewrites** (*Natural & Direct*, *Executive Crisp*, *Conversational*) for every AI-flagged sentence.
   - Allows users to **Accept**, **Edit Manually**, **Regenerate via LLM**, or **Revert** each flagged sentence interactively while watching the document's overall AI score drop in real time.

3. **Multi-Provider LLM Engine (`backend/modules/llm_client.py`)**
   - Supports **OpenAI** (`gpt-4o-mini`), **Google Gemini** (`gemini-2.0-flash`), and **Anthropic Claude** (`claude-3-5-haiku-latest`) via `.env` OR directly inside the web UI's **⚙️ LLM API Config** modal.
   - Includes a built-in deterministic linguistic fallback so the demo works immediately out of the box even before an API key is added.

---

## Quick Start (Docker Compose — Recommended for CEO Setup)

### 1. Clone the repository
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd ai-checker
```

### 2. Configure `.env` (Optional — can also be entered in the UI)
```bash
cp .env.example .env
```
Open `.env` and paste your `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY`. *(You can also skip this and paste an API key directly in the browser UI via the **⚙️ LLM API Config** button).*

### 3. Start with Docker Compose
```bash
docker compose up --build
```

- **Frontend (Nuxt 3 Executive Dashboard)**: [http://localhost:3000](http://localhost:3000)
- **Backend (Python FastAPI + Swagger Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Alternative: Run Locally Without Docker

If you have Python 3.9+ and Node.js 18+ installed locally:
```bash
chmod +x start.sh
./start.sh
```
