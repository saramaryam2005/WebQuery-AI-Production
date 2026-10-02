import os
import json
import asyncio
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional

# Load environment variables from .env file
load_dotenv()

if os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

from app.chatbot.rag_chain import ask_question

router = APIRouter()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_URL.endswith("/"):
    SUPABASE_URL = SUPABASE_URL.rstrip("/")

HEADERS = {
    "apikey": SUPABASE_KEY if SUPABASE_KEY else "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class AuthenticatedChatRequest(BaseModel):
    session_id: str
    title: str
    question: str
    user_id: str


@router.post("/auth/signup")
def signup_user(auth_data: UserAuth):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Database credentials missing in environment.")
    
    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    try:
        res = requests.post(
            signup_url, 
            headers=HEADERS, 
            json={"email": auth_data.email, "password": auth_data.password},
            timeout=10
        )
        data = res.json()

        if res.status_code not in [200, 201]:
            error_msg = data.get("msg") or data.get("error_description") or data.get("message") or "Signup failed"
            raise HTTPException(status_code=res.status_code, detail=error_msg)

        # Handle variations in Supabase signup payload structure safely
        user_obj = data.get("user") or data
        user_id = user_obj.get("id") or auth_data.email
        user_email = user_obj.get("email") or auth_data.email

        return {"message": "Signup successful", "user_id": user_id, "email": user_email}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup request error: {str(e)}")


@router.post("/auth/login")
def login_user(auth_data: UserAuth):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Database credentials missing in environment.")
    
    login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    try:
        res = requests.post(
            login_url, 
            headers=HEADERS, 
            json={"email": auth_data.email, "password": auth_data.password},
            timeout=10
        )
        data = res.json()

        if res.status_code not in [200, 201]:
            error_msg = data.get("error_description") or data.get("msg") or data.get("message") or "Invalid credentials"
            raise HTTPException(status_code=res.status_code, detail=error_msg)

        user_obj = data.get("user", {})
        user_id = user_obj.get("id") or auth_data.email
        access_token = data.get("access_token", "")

        return {"message": "Login successful", "user_id": user_id, "access_token": access_token}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login request error: {str(e)}")


@router.get("/history")
def get_user_history(user_id: Optional[str] = Query(None)):
    if not user_id or user_id == "webquery_anonymous_user":
        return []
    try:
        sess_url = f"{SUPABASE_URL}/rest/v1/sessions?user_id=eq.{user_id}&select=id,title&order=created_at.desc"
        s_res = requests.get(sess_url, headers=HEADERS, timeout=10)
        if s_res.status_code != 200:
            return []
        sessions = s_res.json()
        history = []
        for s in sessions:
            session_id = s.get("id")
            msg_url = f"{SUPABASE_URL}/rest/v1/messages?session_id=eq.{session_id}&select=role,content,sources&order=id.asc"
            m_res = requests.get(msg_url, headers=HEADERS, timeout=10)
            messages = []
            raw_history = []
            if m_res.status_code == 200:
                for m in m_res.json():
                    messages.append({
                        "role": m.get("role", "user"),
                        "content": m.get("content", ""),
                        "sources": m["sources"].split(",") if m.get("sources") else []
                    })
                    raw_history.append({
                        "role": "user" if m.get("role") == "user" else "assistant", 
                        "content": m.get("content", "")
                    })
            history.append({
                "id": session_id,
                "title": s.get("title") or "Saved Chat Session",
                "messages": messages,
                "rawHistory": raw_history
            })
        return history
    except Exception:
        return []


@router.post("/chat")
def chat_endpoint(request: AuthenticatedChatRequest):
    async def event_generator():
        try:
            # 1. Initialize session if missing
            chk_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{request.session_id}&select=id"
            chk_res = requests.get(chk_url, headers=HEADERS, timeout=10)
            if chk_res.status_code == 200 and not chk_res.json():
                ins_sess_url = f"{SUPABASE_URL}/rest/v1/sessions"
                requests.post(
                    ins_sess_url, 
                    headers=HEADERS, 
                    json={
                        "id": request.session_id, 
                        "user_id": request.user_id, 
                        "title": request.question[:20]
                    },
                    timeout=10
                )

            # 2. Call RAG Chain
            result = ask_question(request.question)
            bot_answer = result.get("answer", "I couldn't locate specific references.")
            sources = result.get("sources", [])
            sources_str = ",".join(sources) if sources else ""

            # 3. Stream response tokens
            words = bot_answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                payload = json.dumps({'text': chunk})
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.02)

            # 4. Stream source metadata
            payload_sources = json.dumps({'sources': sources})
            yield f"data: {payload_sources}\n\n"

            # 5. Persist messages to Supabase
            ins_msg_url = f"{SUPABASE_URL}/rest/v1/messages"
            requests.post(
                ins_msg_url, 
                headers=HEADERS, 
                json={
                    "session_id": request.session_id, 
                    "role": "user", 
                    "content": request.question, 
                    "sources": ""
                },
                timeout=10
            )
            requests.post(
                ins_msg_url, 
                headers=HEADERS, 
                json={
                    "session_id": request.session_id, 
                    "role": "bot", 
                    "content": bot_answer, 
                    "sources": sources_str
                },
                timeout=10
            )

        except Exception as e:
            err_payload = json.dumps({'text': f"Pipeline processing anomaly: {str(e)}"})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str):
    try:
        del_url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{session_id}"
        requests.delete(del_url, headers=HEADERS, timeout=10)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))