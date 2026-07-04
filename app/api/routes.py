import os
import traceback
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from app.api.routes import router as api_router

app = FastAPI(title="WebQuery AI Chatbot")

# 1. Global Exception Handler to catch any hidden issues
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("--- CRITICAL RUNTIME ERROR ---")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "details": str(exc)}
    )

# 2. Include backend API routes
app.include_router(api_router, prefix="/api")

# 3. Setup absolute path variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "app", "frontend", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "frontend", "templates")

# 4. Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 5. Serve homepage using modern explicitly named keyword arguments
@app.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    # CRITICAL FIX: Passing request as a distinct keyword parameter prevents the unhashable dict error
    return templates.TemplateResponse(
        request=request, 
        name="index.html"
    )