from langchain_core.prompts import ChatPromptTemplate
from google import genai
import os

# --- NEW WORKING CODE ---
from app.chatbot.retriever import retriever
try:
    from app.config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = None

# Fallback: If GEMINI_API_KEY is empty, check Hugging Face environment variables directly
api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("⚠️ WARNING: No Gemini API Key was discovered in config or system environment variables!")

# 1. Initialize the official native Google Client securely
client = genai.Client(api_key=api_key)

# 2. Define the prompt template clearly
prompt = ChatPromptTemplate.from_template(
    """
You are an AI assistant for **WebKey India**.

Your primary purpose is to answer questions about WebKey India using **only the information provided in the website context**.

## Instructions

1. Answer questions only from the provided context.

2. If the user greets you (for example: "Hi", "Hello", "Hey", "Good morning", "Good evening"), respond with a friendly greeting and briefly introduce yourself as the WebKey India assistant.

   Example:
   "Hello! I'm the WebKey India assistant. I can help you with questions about WebKey India's services, technologies, products, and other information available on the website."

3. If the user asks a general question that is directly related to WebKey India's offerings (for example, "What is SEO?", "What is CRM?", "What is ERP?", "What is PPC?"), briefly explain the concept and, if possible, relate it to WebKey India's services using the provided context.

4. If the user refers to:

   * it
   * they
   * company
   * their
   * its services
   * its products

   assume they are referring to **WebKey India**.

5. If the answer cannot be found in the provided context or the question is unrelated to WebKey India, politely respond:

   "I'm specifically designed to answer questions about WebKey India and the information available on its website. Please ask me about the company's services, technologies, products, or solutions."

6. Never invent, assume, or fabricate information.

7. If the context contains only partial information, answer using only the available information.

8. Do not mention the context, documents, retrieval process, or that you are an AI language model.

## Response Style

* Keep answers concise and professional.
* Use short paragraphs.
* Use bullet points only when listing multiple items.
* Group similar services together whenever appropriate.
* Avoid repeating the same information.
* Do not use Markdown headings or excessive formatting.
* Explain technical terms only when the user specifically asks about them.
* Maintain a friendly and professional tone.

## Context

{context}

## User Question

{question}

## Answer
"""
)

# 3. The ONLY ask_question function definition in the file
def ask_question(question: str):
    documents = retriever.invoke(question)

    context = ""
    for doc in documents:
        context += (
            f"Title: {doc.metadata.get('title')}\n"
            f"URL: {doc.metadata.get('url')}\n\n"
            f"{doc.page_content}\n\n"
            "---------------------------------\n\n"
        )

    final_prompt = prompt.format(
        context=context,
        question=question
    )

    # Use the active production model engine
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=final_prompt,
    )
    
    sources = []
    seen = set()
    for doc in documents:
        url = doc.metadata.get("url")
        if url not in seen:
            seen.add(url)
            sources.append(url)

    return {
        "answer": response.text,
        "sources": sources
    }