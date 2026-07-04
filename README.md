---
title: Web Query AI Chatbot
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# WebQuery AI

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about a website using semantic search and Google's Gemini model.

The application scrapes website content, generates vector embeddings, stores them in ChromaDB, retrieves the most relevant information for a user query, and generates context-aware responses through a FastAPI backend.

![Chatbot UI](chatbot.png)

## Demo Video

🎥 [Watch the Demo](https://youtu.be/9vdJOx3UkR8?si=JjcHPklDRLW9BcQt)
---

## Features

* Website scraping using Selenium
* Text cleaning and chunking
* Semantic embeddings using Sentence Transformers
* Vector storage with ChromaDB
* Retrieval-Augmented Generation (RAG)
* Google Gemini integration
* FastAPI REST API
* Interactive chatbot interface built with HTML, CSS, and JavaScript

---

## Architecture
```text
                          ┌─────────────────────┐
                          │    Website URLs     │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          Selenium Web Scraper
                                     │
                                     ▼
                         Text Cleaning & Chunking
                                     │
                                     ▼
                     SentenceTransformer Embeddings
                                     │
                                     ▼
                                ChromaDB
                                     ▲
                                     │
                           Query Embedding
                                     ▲
                                     │
                              User Question
                                     │
                                     ▼
                      Retrieve Relevant Chunks
                                     │
                                     ▼
                    Prompt + Retrieved Context
                                     │
                                     ▼
                          Google Gemini LLM
                                     │
                                     ▼
                              FastAPI Backend
                                     │
                                     ▼
                       HTML • CSS • JavaScript UI
```

---

## Tech Stack

| Category        | Technologies          |
| --------------- | --------------------- |
| Backend         | FastAPI, Python       |
| Frontend        | HTML, CSS, JavaScript |
| LLM             | Google Gemini         |
| Vector Database | ChromaDB              |
| Embeddings      | Sentence Transformers |
| Web Scraping    | Selenium              |
| Data Validation | Pydantic              |

---

## Workflow

1. Scrape website content.
2. Clean and split the text into chunks.
3. Generate embeddings for every chunk.
4. Store embeddings in ChromaDB.
5. Convert the user's question into an embedding.
6. Retrieve the most relevant chunks.
7. Send the retrieved context and question to Gemini.
8. Return the generated answer through the FastAPI API.
9. Display the response in the chatbot interface.

---

## Installation

```bash
git clone <repository-url>

cd WebQuery-AI

python -m venv .venv

# Activate virtual environment

pip install -r requirements.txt
```

Create a `.env` file:

```env
GOOGLE_API_KEY=your_api_key_here
```

Create the vector database:

```bash
python -m tests.test_index
```

Run the application:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## Future Improvements

* Support multiple websites
* Scheduled website re-indexing
* Response caching
* Streaming LLM responses
* Authentication and user sessions
* Hybrid keyword + semantic retrieval

---

