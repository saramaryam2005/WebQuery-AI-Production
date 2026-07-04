import os
import sys
from pathlib import Path

# Explicitly add the project root to the Python path for Vercel
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
    
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from app.api.routes import router as chat_router
from app.frontend.routes import router as frontend_router
from fastapi.staticfiles import StaticFiles
app = FastAPI(
    title="WebQuery AI",
    version="1.0.0"
)
app.mount(
    "/static",
    StaticFiles(directory="app/frontend/static"),
    name="static"
)
app.include_router(frontend_router)
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=False)