import os
from langchain_pinecone import PineconeVectorStore
from app.chatbot.embeddings import embedding_model
from pinecone import Pinecone

INDEX_NAME = "webquery-index"  # Let's use a fresh index name

vector_store = PineconeVectorStore(
    index_name=INDEX_NAME,
    embedding=embedding_model,
    pinecone_api_key=os.getenv("PINECONE_API_KEY")
)