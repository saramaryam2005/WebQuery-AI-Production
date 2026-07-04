import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.chatbot.rag_chain import ask_question

router = APIRouter()

# Extract database credentials securely from system architecture environment
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is missing on runtime context!")
    # Connect directly to the cloud instance
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build production schemas seamlessly on Supabase
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Supabase cloud database system tables initialized perfectly.")
    except Exception as e:
        print(f"❌ Failed to structure initial database configurations: {str(e)}")

# Safe instantiation during runtime imports
init_db()

class ChatRequest(BaseModel):
    session_id: str
    title: str
    question: str

@router.get("/history")
def get_user_history(user_id: Optional[str] = Cookie(None)):
    if not user_id:
        return []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM sessions WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        sessions_rows = cursor.fetchall()
        
        history = []
        for s_row in sessions_rows:
            session_id = s_row["id"]
            cursor.execute("SELECT role, content, sources FROM messages WHERE session_id = %s ORDER BY id ASC", (session_id,))
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
        cursor.close()
        conn.close()
        return history
    except Exception as e:
        if 'conn' in locals() and not conn.closed: conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
def chat_endpoint(request: ChatRequest, response: Response, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id, max_age=31536000, httponly=False, samesite="lax", path="/")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sessions WHERE id = %s", (request.session_id,))
        session_exists = cursor.fetchone()
        
        if not session_exists:
            cursor.execute("INSERT INTO sessions (id, user_id, title) VALUES (%s, %s, %s)", 
                           (request.session_id, user_id, request.title))
            conn.commit()
            
        result = ask_question(request.question)
        
        sources_str = ",".join(result["sources"]) if ("sources" in result and result["sources"]) else ""
        bot_answer = result.get("answer", "I couldn't find an answer for that.")
        
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (%s, 'user', %s, '')", 
                       (request.session_id, request.question))
        cursor.execute("INSERT INTO messages (session_id, role, content, sources) VALUES (%s, 'bot', %s, %s)", 
                       (request.session_id, bot_answer, sources_str))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = %s AND role = 'user'", (request.session_id,))
        user_msg_count = cursor.fetchone()['count']
        
        if user_msg_count <= 1:
            q_text = request.question
            updated_title = (q_text[:18] + "...") if len(q_text) > 18 else q_text
            cursor.execute("UPDATE sessions SET title = %s WHERE id = %s", (updated_title, request.session_id))
            conn.commit()

        cursor.close()
        conn.close()
        return result
    except Exception as e:
        if 'conn' in locals() and not conn.closed: conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str, user_id: Optional[str] = Cookie(None)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Clean session tracking tables out completely from permanent memory storage
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        if 'conn' in locals() and not conn.closed: conn.close()
        raise HTTPException(status_code=500, detail=str(e))