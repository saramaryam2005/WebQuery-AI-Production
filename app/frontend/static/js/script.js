let allSessions = []; 
let currentSessionId = null;

// On startup, fetch user history from SQLite database
window.onload = async () => {
    await fetchHistoryFromServer();
};

async function fetchHistoryFromServer() {
    try {
        const response = await fetch("/api/history", { credentials: "same-origin" });
        let data = await response.json();
        
        if (Array.isArray(data)) {
            allSessions = data;
        } else {
            allSessions = [];
        }
        
        if (allSessions.length > 0) {
            currentSessionId = allSessions[0].id;
            switchSession(currentSessionId);
        } else {
            createNewChat();
        }
    } catch (error) {
        console.error("Failed to load historical database session:", error);
        allSessions = [];
        createNewChat();
    }
}

function createNewChat() {
    currentSessionId = "session_" + Date.now();
    
    const welcomeText = "Hello! 👋 I'm the WebKey India smart assistant. Ask me anything about our services, products, or technologies! 🚀";
    
    const newSession = {
        id: currentSessionId,
        title: "✨ New Chat Session",
        messages: [{ content: welcomeText, role: "bot" }],       
        rawHistory: []      
    };
    allSessions.unshift(newSession); 
    
    renderSidebar();
    clearChatDisplay();
    appendMessage(welcomeText, "bot");
}

async function sendMessage() {
    const inputElement = document.getElementById("user-input");
    const question = inputElement.value.trim();
    if (!question) return;

    let session = allSessions.find(s => s.id === currentSessionId);
    if (!session) return;
    
    if (session.messages.length <= 1) {
        session.title = question.length > 18 ? "💬 " + question.substring(0, 18) + "..." : "💬 " + question;
    }

    appendMessage(question, "user");
    session.messages.push({ content: question, role: "user" });
    inputElement.value = "";
    renderSidebar();

    const loadingId = appendMessage("Thinking... 🤖", "bot-loading");

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                session_id: currentSessionId,
                title: session.title,
                question: question
            })
        });

        const data = await response.json();
        removeElement(loadingId);
        
        // UNIFIED PROPERTY FIX: Fallback checks to ensure text fields never output 'undefined'
        const botResponseText = data.answer || data.content || "I'm sorry, I couldn't process that.";
        const sourcesList = data.sources || [];

        appendMessage(botResponseText, "bot", sourcesList);
        
        session.messages.push({ content: botResponseText, role: "bot", sources: sourcesList });
        if (!session.rawHistory) session.rawHistory = [];
        session.rawHistory.push({ role: "user", content: question });
        session.rawHistory.push({ role: "assistant", content: botResponseText });

    } catch (error) {
        removeElement(loadingId);
        appendMessage("An error occurred. Please try again. ⚠️", "bot-error");
        console.error("Inbound API Error Log:", error);
    }
}

function renderSidebar() {
    const listContainer = document.getElementById("chat-history-list");
    if (!listContainer) return;
    listContainer.innerHTML = ""; 

    allSessions.forEach(session => {
        const li = document.createElement("li");
        li.className = `history-item ${session.id === currentSessionId ? 'active' : ''}`;
        
        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.innerText = session.title;
        titleSpan.onclick = () => switchSession(session.id);
        
        const delBtn = document.createElement("button");
        delBtn.className = "delete-btn";
        delBtn.innerHTML = "🗑️";
        delBtn.onclick = (e) => {
            e.stopPropagation(); 
            deleteSessionFromServer(session.id);
        };

        li.appendChild(titleSpan);
        li.appendChild(delBtn);
        listContainer.appendChild(li);
    });
}

function switchSession(sessionId) {
    currentSessionId = sessionId;
    renderSidebar();
    clearChatDisplay();

    const session = allSessions.find(s => s.id === currentSessionId);
    if (session && session.messages) {
        session.messages.forEach(msg => {
            // UNIFIED PROPERTY FIX: Extract string safely whether it comes from DB (content) or live feed
            const messageText = msg.content || msg.text || "";
            appendMessage(messageText, msg.role, msg.sources || []);
        });
    }
}

function clearChatDisplay() { 
    const chatBox = document.getElementById("chat-box");
    if (chatBox) chatBox.innerHTML = ""; 
}

function appendMessage(text, role, sources = []) {
    const chatBox = document.getElementById("chat-box");
    if (!chatBox) return;
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;
    
    let contentHtml = `<p>${text}</p>`;
    if (sources && sources.length > 0) {
        contentHtml += `<div class="sources" style="font-size:11px; color:#888; margin-top:8px;">🔍 Sources: ${sources.join(', ')}</div>`;
    }
    
    msgDiv.innerHTML = contentHtml;
    const uniqueId = "msg_" + Math.random().toString(36).substring(2, 9);
    msgDiv.id = uniqueId;
    
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return uniqueId;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

async function deleteSessionFromServer(sessionId) {
    if (!confirm("Are you sure you want to delete this conversation permanently?")) return;

    try {
        const response = await fetch(`/api/session/${sessionId}`, {
            method: "DELETE"
        });

        if (response.ok) {
            allSessions = allSessions.filter(s => s.id !== sessionId);
            if (currentSessionId === sessionId) {
                if (allSessions.length > 0) {
                    currentSessionId = allSessions[0].id;
                    switchSession(currentSessionId);
                } else {
                    createNewChat();
                }
            } else {
                renderSidebar();
            }
        } else {
            alert("Failed to delete session resource from database");
        }
    } catch (error) {
        console.error("Deletion API Transaction failure:", error);
    }
}