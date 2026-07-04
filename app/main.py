import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router as api_router

app = FastAPI(title="WebQuery AI Chatbot")

# 1. DYNAMICALLY RESOLVE ABSOLUTE FILE PATHS
# This prevents Hugging Face from getting lost in nested directory structures
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # points to 'app' folder
STATIC_DIR = os.path.normpath(os.path.join(CURRENT_DIR, "frontend", "static"))
TEMPLATE_DIR = os.path.normpath(os.path.join(CURRENT_DIR, "frontend", "templates"))

print("\n" + "="*60)
print(f"📁 MOUNTING STATIC FILES FROM: {STATIC_DIR}")
print(f"📄 SERVING index.html FROM: {TEMPLATE_DIR}")
print("="*60 + "\n")

# 2. MOUNT STATIC ASSETS (CSS, JS, Images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 3. INCLUDE DATABASE & CHAT ROUTES
app.include_router(api_router, prefix="/api")

# 4. SERVE FRONTEND INDEX PAGE
@app.get("/")
def read_root():
    index_path = os.path.join(TEMPLATE_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"index.html not found at target location: {index_path}"}
    return FileResponse(index_path)

# Allows running directly via 'python app/main.py' if needed locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=7860, reload=True)