import sqlite3
import os
import uuid
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.chatbot.rag_chain import ask_question

router = APIRouter()

# Global connection placeholder for Hugging Face RAM mode
_hf_memory_conn = None

# Calculate paths for local fallback
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
DB_PATH = os.path.normpath(os.path.join(PROJECT_ROOT, "chatbot.db"))

def is_hf():
    return os.environ.get("RUNNING_ON_HF") == "true" or os.environ.get("RUNNING_ON_HF") == "1"

def get_db_connection():
    global _hf_memory_conn
    
    if is_hf():
        if _hf_memory_conn is None:
            # Create a truly persistent, shared in-memory database workspace
            _hf_memory_conn = sqlite3.connect("file:hf_shared_mem_db?mode=memory&cache=shared", uri=True, timeout=15.0)
            _hf_memory_conn.row_factory = sqlite3.Row
            # Enable quick database cascading deletes
            _hf_memory_conn.execute("PRAGMA foreign_keys = ON;")
        return _hf_memory_conn
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = EXTRA;")
        conn.execute("PRAGMA journal_mode = DELETE;")
        return conn

def safe_close(conn):
    """Only close the database connection if we are running locally on localhost."""
    if not is_hf():
        conn.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    safe_close(conn)

init_db()

class ChatRequest(BaseModel):
    session_id: str
    title: str
    question: str

@router.get("/history")
def get_user_history(user_id: Optional[str] = Cookie(None)):
    if not user_id:
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    sessions_rows = cursor.fetchall()
    
    history = []
    for s_row in sessions_rows:
        session_id = s_row["id"]
        cursor.execute("SELECT role, content, sources FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        msg_rows = cursor.fetchall()
        
        messages = []
        raw_history = []
        for m in msg_rows:
            msg_data = {"content": m["content"], "role": m["role"]}
            if m["sources"]:
                msg_data["sources"] = m["sources"].split(",")
            messages.append(msg_data)
            
            api_role = "user" if m["role"] == "user" else "assistant"
            raw_history.append({"role": api_role, "content": m["content"]})
            
        history.append({
            "id": session_id,
            "title": s_row["title"],
            "messages": messages,
            "rawHistory": raw_history
        })
    safe_close(conn)
    return history

@router.post("/chat")
def chat_endpoint(request: ChatRequest, response: Response, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id, max_age=31536000, httponly=False, samesite="lax", path="/")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (request.session_id,))
        session_exists = cursor.fetchone()
        
        if not session_exists:
            cursor.execute("INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)", 
                           (request.session_id, user_id, request.title))
            conn.commit()
            
        result = ask_question(request.question)
        
        sources_str = ",".join(result["sources"]) if ("sources" in result and result["sources"]) else ""
        bot_answer = result.get("answer", "I couldn't find an answer for that.")
        
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (?, 'user', ?, '')", 
                       (request.session_id, request.question))
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (?, 'bot', ?, ?)", 
                       (request.session_id, bot_answer, sources_str))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'", (request.session_id,))
        user_msg_count = cursor.fetchone()[0]
        
        if user_msg_count <= 1:
            q_text = request.question
            updated_title = (q_text[:18] + "...") if len(q_text) > 18 else q_text
            cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (updated_title, request.session_id))
            conn.commit()

        safe_close(conn)
        return result
    except Exception as e:
        if 'conn' in locals(): safe_close(conn)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify the session belongs to this user before deleting
        cursor.execute("SELECT id FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        if not cursor.fetchone():
            safe_close(conn)
            raise HTTPException(status_code=404, detail="Not found")
            
        # Execute the delete action smoothly
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        
        safe_close(conn)
        return {"status": "success"}
    except Exception as e:
        if 'conn' in locals(): safe_close(conn)
        raise HTTPException(status_code=500, detail=str(e))