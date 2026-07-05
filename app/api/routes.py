import os
import uuid
import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional

# Force Gemini environment mappings safely
if os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

from app.chatbot.rag_chain import ask_question

router = APIRouter()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Remove trailing slash if present in URL
if SUPABASE_URL and SUPABASE_URL.endswith("/"):
    SUPABASE_URL = SUPABASE_URL.rstrip("/")

HEADERS = {
    "apikey": SUPABASE_KEY if SUPABASE_KEY else "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

class ChatRequest(BaseModel):
    session_id: str
    title: str
    question: str
    user_id: Optional[str] = None  # Frontend blocks cookies fallback tracking

@router.get("/history")
def get_user_history(user_id: Optional[str] = Query(None)):
    active_user = user_id if user_id else "webquery_anonymous_user"
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        sess_url = f"{SUPABASE_URL}/rest/v1/sessions?user_id=eq.{active_user}&select=id,title&order=created_at.desc"
        s_res = requests.get(sess_url, headers=HEADERS)
        if s_res.status_code != 200:
            return []
        
        sessions = s_res.json()
        history = []
        
        for s in sessions:
            session_id = s["id"]
            msg_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{session_id}&select=role,content,sources&order=id.asc"
            m_res = requests.get(msg_url, headers=HEADERS)
            
            messages = []
            raw_history = []
            if m_res.status_code == 200:
                for m in m_res.json():
                    messages.append({
                        "role": m["role"],
                        "content": m["content"],
                        "sources": m["sources"].split(",") if m.get("sources") else []
                    })
                    raw_history.append({
                        "role": "user" if m["role"] == "user" else "assistant",
                        "content": m["content"]
                    })
            
            history.append({
                "id": session_id,
                "title": s["title"] if s.get("title") else "Saved Chat Session",
                "messages": messages,
                "rawHistory": raw_history
            })
        return history
    except Exception:
        return []

@router.post("/chat")
def chat_endpoint(request: ChatRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"answer": "Cloud database credentials configuration missing.", "sources": []}

    active_user = request.user_id if request.user_id else "webquery_anonymous_user"

    try:
        # Check if session exists
        chk_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}&select=id"
        chk_res = requests.get(chk_url, headers=HEADERS)
        
        if chk_res.status_code == 200 and not chk_res.json():
            ins_sess_url = f"{SUPABASE_URL}/rest/v1/sessions"
            requests.post(ins_sess_url, headers=HEADERS, json={
                "id": request.session_id, 
                "user_id": active_user, 
                "title": request.title if request.title else "New Chat Session"
            })
            
        result = ask_question(request.question)
        bot_answer = result.get("answer", "I couldn't locate specific references.")
        sources_str = ",".join(result.get("sources", [])) if result.get("sources") else ""
        
        # Insert Chat Data
        ins_msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "user", "content": request.question, "sources": ""})
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "bot", "content": bot_answer, "sources": sources_str})
        
        # Auto Update Title on First Message
        count_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{request.session_id}&role=eq.user&select=id"
        c_res = requests.get(count_url, headers=HEADERS)
        if c_res.status_code == 200 and len(c_res.json()) <= 1:
            updated_title = request.question[:18] + "..." if len(request.question) > 18 else request.question
            upd_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}"
            requests.patch(upd_url, headers=HEADERS, json={"title": updated_title})

        return result
    except Exception as e:
        return {"answer": "Database pipeline sync active. Please submit your question again.", "sources": []}

@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str):
    if not SUPABASE_URL:
        raise HTTPException(status_code=500, detail="Database environment unavailable.")
    try:
        del_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{session_id}"
        requests.delete(del_url, headers=HEADERS)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))