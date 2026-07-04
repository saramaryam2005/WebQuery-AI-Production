import os
import uuid
import requests
from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.chatbot.rag_chain import ask_question

router = APIRouter()

# Extract credentials securely from Hugging Face environment context
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# HTTP headers required to securely interact with Supabase REST interface
HEADERS = {
    "apikey": SUPABASE_KEY if SUPABASE_KEY else "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def init_db():
    # Tables are auto-managed via the REST API layers, no complex DDL configuration needed!
    print("✅ Web API communication context configured for Supabase.")

init_db()

class ChatRequest(BaseModel):
    session_id: str
    title: str
    question: str

@router.get("/history")
def get_user_history(user_id: Optional[str] = Cookie(None)):
    if not user_id or not SUPABASE_URL:
        return []
    try:
        # 1. Fetch all active sessions linked to this user cookie context
        sess_url = f"{SUPABASE_URL}/rest/v1/sessions?user_id=eq.{user_id}&select=id,title&order=created_at.desc"
        s_res = requests.get(sess_url, headers=HEADERS)
        if s_res.status_code != 200:
            return []
        
        sessions = s_res.json()
        history = []
        
        # 2. Extract corresponding message blocks chronologically
        for s in sessions:
            session_id = s["id"]
            msg_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{session_id}&select=role,content,sources&order=id.asc"
            m_res = requests.get(msg_url, headers=HEADERS)
            
            messages = []
            raw_history = []
            if m_res.status_code == 200:
                for m in m_res.json():
                    msg_data = {"content": m["content"], "role": m["role"]}
                    if m.get("sources"):
                        msg_data["sources"] = m["sources"].split(",")
                    messages.append(msg_data)
                    
                    api_role = "user" if m["role"] == "user" else "assistant"
                    raw_history.append({"role": api_role, "content": m["content"]})
            
            history.append({
                "id": session_id,
                "title": s["title"],
                "messages": messages,
                "rawHistory": raw_history
            })
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
def chat_endpoint(request: ChatRequest, response: Response, user_id: Optional[str] = Cookie(None)):
    if not user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id, max_age=31536000, httponly=False, samesite="lax", path="/")

    if not SUPABASE_URL:
        raise HTTPException(status_code=500, detail="Supabase runtime variables are missing.")

    try:
        # Check if session exists in cloud DB context
        chk_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}&select=id"
        chk_res = requests.get(chk_url, headers=HEADERS)
        
        if chk_res.status_code == 200 and not chk_res.json():
            # Session entry setup is required
            ins_sess_url = f"{SUPABASE_URL}/rest/v1/sessions"
            payload = {"id": request.session_id, "user_id": user_id, "title": request.title}
            requests.post(ins_sess_url, headers=HEADERS, json=payload)
            
        result = ask_question(request.question)
        sources_str = ",".join(result["sources"]) if ("sources" in result and result["sources"]) else ""
        bot_answer = result.get("answer", "I couldn't find an answer for that.")
        
        # Write conversational payloads via sequential REST insertions
        ins_msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "user", "content": request.question, "sources": ""})
        requests.post(ins_msg_url, headers=HEADERS, json={"session_id": request.session_id, "role": "bot", "content": bot_answer, "sources": sources_str})
        
        # Title auto-updater logic for first entry
        count_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{request.session_id}&role=eq.user&select=id"
        c_res = requests.get(count_url, headers=HEADERS)
        if c_res.status_code == 200 and len(c_res.json()) <= 1:
            q_text = request.question
            updated_title = (q_text[:18] + "...") if len(q_text) > 18 else q_text
            upd_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}"
            requests.patch(upd_url, headers=HEADERS, json={"title": updated_title})

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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