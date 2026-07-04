import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 1. Force load your environment variables from the root folder
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Set the global environment variable that LangChain relies on natively
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 3. Instantiate using Google's active replacement model
embedding_model = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001"  # <-- Swapped to the live, working model
)