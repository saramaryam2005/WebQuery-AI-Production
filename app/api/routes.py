import os
import sqlite3
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import List, Dict, Optional

# Force Gemini environment mappings safely
if os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

from app.chatbot.rag_chain import ask_question

router = APIRouter()

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "chatbot.db"))

def init_local_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

# Auto boot local schema tracker
init_local_db()

class ChatRequest(BaseModel):
    session_id: str
    title: str
    question: str

@router.get("/history")
def get_user_history(user_id: Optional[str] = Cookie(None)):
    if not user_id:
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        sessions = cursor.fetchall()
        history = []
        
        for s in sessions:
            cursor.execute("SELECT role, content, sources FROM messages WHERE session_id = ? ORDER BY id ASC", (s["id"],))
            rows = cursor.fetchall()
            messages = []
            raw_history = []
            
            for r in rows:
                messages.append({
                    "role": r["role"],
                    "content": r["content"],
                    "sources": r["sources"].split(",") if r["sources"] else []
                })
                raw_history.append({
                    "role": "user" if r["role"] == "user" else "assistant",
                    "content": r["content"]
                })
            
            history.append({
                "id": s["id"],
                "title": s["title"] if s["title"] else "Saved Chat Session",
                "messages": messages,
                "rawHistory": raw_history
            })
        conn.close()
        return history
    except Exception:
        return []

@router.post("/chat")
def chat_endpoint(request: ChatRequest, response: Response, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        import uuid
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id, max_age=31536000, httponly=False, samesite="none", secure=True, path="/")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (request.session_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)", 
                           (request.session_id, user_id, request.title if request.title else "New Chat Session"))
            
        result = ask_question(request.question)
        bot_answer = result.get("answer", "I couldn't locate specific references.")
        sources_str = ",".join(result.get("sources", [])) if result.get("sources") else ""
        
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (?, ?, ?, ?)", (request.session_id, "user", request.question, ""))
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (?, ?, ?, ?)", (request.session_id, "bot", bot_answer, sources_str))
        
        cursor.execute("SELECT count(*) FROM messages WHERE session_id = ? AND role = 'user'", (request.session_id,))
        if cursor.fetchone()[0] <= 1:
            updated_title = request.question[:18] + "..." if len(request.question) > 18 else request.question
            cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (updated_title, request.session_id))
            
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        return {"answer": "Local sequence online. Please re-submit entry.", "sources": []}

@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))