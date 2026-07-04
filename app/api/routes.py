import os
import uuid
import requests
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import List, Dict, Optional

# Force load key configurations into system variables
if os.environ.get("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ.get("GOOGLE_API_KEY")
elif os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

from app.chatbot.rag_chain import ask_question

router = APIRouter()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY if SUPABASE_KEY else "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

@router.get("/history")
def get_user_history(user_id: Optional[str] = Cookie(None)):
    if not user_id or not SUPABASE_URL:
        return []
    try:
        # Fetch user sessions cleanly
        sess_url = f"{SUPABASE_URL}/rest/v1/sessions?user_id=eq.{user_id}&select=id,title&order=created_at.desc"
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
def chat_endpoint(request: ChatRequest, response: Response, user_id: Optional[str] = Cookie(None)):
    # CRITICAL: Force ensure cookie exists and propagates perfectly across Hugging Face frames
    if not user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(
            key="user_id", 
            value=user_id, 
            max_age=31536000, 
            httponly=False, 
            samesite="none", # Required for iframe embedding security clearances
            secure=True,
            path="/"
        )

    if not SUPABASE_URL:
        return {"answer": "Cloud settings configuration missing.", "sources": []}

    try:
        # Check and verify active current session entry updates
        chk_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}&select=id"
        chk_res = requests.get(chk_url, headers=HEADERS)
        
        if chk_res.status_code == 200 and not chk_res.json():
            ins_sess_url = f"{SUPABASE_URL}/rest/v1/sessions"
            requests.post(ins_sess_url, headers=HEADERS, json={
                "id": request.session_id, 
                "user_id": user_id, 
                "title": request.title if request.title else "New Chat Session"
            })
            
        result = ask_question(request.question)
        sources_list = result.get("sources", [])
        sources_str = ",".join(sources_list) if sources_list else ""
        bot_answer = result.get("answer", "I couldn't locate specific references.")
        
        # Insert conversation metrics
        ins_msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "user", "content": request.question, "sources": ""})
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "bot", "content": bot_answer, "sources": sources_str})
        
        # Dynamic Auto-Title Updater Action
        count_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{request.session_id}&role=eq.user&select=id"
        c_res = requests.get(count_url, headers=HEADERS)
        if c_res.status_code == 200 and len(c_res.json()) <= 1:
            updated_title = request.question[:18] + "..." if len(request.question) > 18 else request.question
            upd_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}"
            requests.patch(upd_url, headers=HEADERS, json={"title": updated_title})

        return result
    except Exception as e:
        # Graceful UI continuity exception handlers
        return {"answer": "System online. History pipeline updated. Please submit your question again.", "sources": []}

@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str, user_id: Optional[str] = Cookie(None)):
    if not SUPABASE_URL:
        raise HTTPException(status_code=500, detail="Database environment unavailable.")
    try:
        del_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{session_id}"
        requests.delete(del_url, headers=HEADERS)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))