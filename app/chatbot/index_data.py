import json
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from app.chatbot.chunker import create_chunks
from app.chatbot.preprocessor import clean_text
from app.chatbot.vector_store import vector_store

# Load environment variables (.env)
load_dotenv()

DATA_FILE = Path("data/raw/pages.json")

def load_pages():
    """Load all scraped website pages."""
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)
    
def batch_documents(documents, ids, batch_size=20):
    """Yield documents and IDs in batches."""
    for i in range(0, len(documents), batch_size):
        yield (
            documents[i:i + batch_size],
            ids[i:i + batch_size]
        )

def index_website():
    if not DATA_FILE.exists():
        print(f"❌ Error: {DATA_FILE} not found. Run your scraper first!")
        return

    pages = load_pages()
    documents = []
    ids = []

    print("📖 Processing and chunking website data...")
    for page in pages:
        # Keep your original text cleaning and chunking logic
        cleaned_text = clean_text(page["content"])
        chunks = create_chunks(cleaned_text)

        for index, chunk in enumerate(chunks):
            # Safe check to skip empty chunks
            if not chunk.strip():
                continue

            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "url": page["url"],
                        "title": page["title"]
                    }
                )
            )
            # Pinecone IDs work beautifully with strings like this
            ids.append(f"{page['url']}_{index}")

    print(f"🚀 Uploading {len(documents)} chunks to Pinecone in batches...")
    
    # Send chunks to Pinecone using your batching generator
    for batch_docs, batch_ids in batch_documents(documents, ids, batch_size=20):
        try:
            vector_store.add_documents(
                documents=batch_docs,
                ids=batch_ids
            )
            print(f"✅ Indexed {len(batch_docs)} documents...")
            
            # 💡 INCREASED SLEEP TIME TO 3 SECONDS TO AVOID GOOGLE 429 LIMITS
            time.sleep(3) 
            
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")