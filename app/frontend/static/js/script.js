// --- GLOBAL VARIABLE MATRIX ---
let allSessions = [];
let currentSessionId = null;

// LocalStorage se unique user_id uthaiye (Null agar user logged-in nahi hai)
let currentUserId = localStorage.getItem("chat_user_id") || null;

// --- AUTHENTICATION STATE CONTROLLER ---
window.addEventListener("DOMContentLoaded", () => {
    const authOverlay = document.getElementById("auth-overlay");
    const logoutBtn = document.getElementById("btn-logout");

    if (currentUserId) {
        // User logged in hai: Form chupao, Logout dikhao, History load karo
        authOverlay.style.display = "none";
        logoutBtn.style.display = "block";
        fetchHistoryFromServer();
    } else {
        // User logged out hai: Form dikhao, Logout chupao
        authOverlay.style.display = "flex";
        logoutBtn.style.display = "none";
    }
});

// --- SIGNUP PROCESS TRIGGER ---
document.getElementById("btn-signup").addEventListener("click", async () => {
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value.trim();
    const errorEl = document.getElementById("auth-error");

    if (!email || !password) {
        errorEl.innerText = "Please fill in all details.";
        errorEl.style.display = "block";
        return;
    }

    try {
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert("Account created successfully! Please click 'Login' now.");
            errorEl.style.display = "none";
        } else {
            errorEl.innerText = data.detail || "Signup failed.";
            errorEl.style.display = "block";
        }
    } catch (e) {
        errorEl.innerText = "Backend communication failed.";
        errorEl.style.display = "block";
    }
});

// --- LOGIN PROCESS TRIGGER ---
document.getElementById("btn-login").addEventListener("click", async () => {
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value.trim();
    const errorEl = document.getElementById("auth-error");

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (res.ok) {
            // Token aur user_id ko local storage mein save kijiye
            localStorage.setItem("chat_user_id", data.user_id);
            localStorage.setItem("chat_token", data.access_token);
            
            // Screen update kijiye
            document.getElementById("auth-overlay").style.display = "none";
            window.location.reload(); // Page reload karke automatic clean state initialize hogi
        } else {
            errorEl.innerText = data.detail || "Invalid email or password.";
            errorEl.style.display = "block";
        }
    } catch (e) {
        errorEl.innerText = "Authentication error.";
        errorEl.style.display = "block";
    }
});

// --- LOGOUT PROCESS TRIGGER ---
document.getElementById("btn-logout").addEventListener("click", () => {
    localStorage.removeItem("chat_user_id");
    localStorage.removeItem("chat_token");
    window.location.reload(); // Instant clean state
});

// --- CHAT HISTORY INTEGRATION LAYER ---
async function fetchHistoryFromServer() {
    if (!currentUserId) return;
    try {
        // Securely pass user_id as a query parameter
        const response = await fetch(`/api/history?user_id=${currentUserId}`);
        let data = await response.json();
        
        if (Array.isArray(data)) {
            allSessions = data;
        } else {
            allSessions = [];
        }
        renderHistoryList();
        
        if (allSessions.length > 0) {
            loadSession(allSessions[0].id);
        } else {
            createNewChat();
        }
    } catch (error) {
        console.error("Error loading chat history:", error);
    }
}

function renderHistoryList() {
    const listEl = document.getElementById("chat-history-list");
    listEl.innerHTML = "";
    
    allSessions.forEach(session => {
        const item = document.createElement("li");
        item.className = `history-item ${session.id === currentSessionId ? 'active' : ''}`;
        item.onclick = () => loadSession(session.id);
        
        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.innerText = session.title || "Saved Chat Session";
        
        const delBtn = document.createElement("button");
        delBtn.className = "delete-btn";
        delBtn.innerHTML = "🗑️";
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteSessionFromServer(session.id);
        };
        
        item.appendChild(titleSpan);
        item.appendChild(delBtn);
        listEl.appendChild(item);
    });
}

function loadSession(sessionId) {
    currentSessionId = sessionId;
    const session = allSessions.find(s => s.id === sessionId);
    const chatBox = document.getElementById("chat-box");
    chatBox.innerHTML = "";
    
    if (session && session.messages) {
        session.messages.forEach(msg => {
            appendMessage(msg.role === "user" ? "user" : "bot", msg.content, msg.sources);
        });
    }
    renderHistoryList();
}

function createNewChat() {
    currentSessionId = "session_" + Date.now();
    document.getElementById("chat-box").innerHTML = `
        <div class="message bot">
            Hello! 👋 I'm the WebKey India smart assistant. Ask me anything about our services, products, or technologies! 🚀
        </div>
    `;
    renderHistoryList();
}

// --- SECURE MESSAGE PIPELINE ---
// --- SECURE MESSAGE PIPELINE WITH STREAMING SUPPORT ---
async function sendMessage() {
    const inputEl = document.getElementById("user-input");
    const question = inputEl.value.trim();
    if (!question || !currentUserId) return;
    
    appendMessage("user", question);
    inputEl.value = "";
    
    const chatBox = document.getElementById("chat-box");
    
    // Create an empty bot message bubble where tokens will be streamed dynamically
    const botMsgDiv = document.createElement("div");
    botMsgDiv.className = "message bot";
    const botTextPara = document.createElement("p");
    botTextPara.innerText = "Thinking...";
    botMsgDiv.appendChild(botTextPara);
    chatBox.appendChild(botMsgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSessionId,
                title: question.substring(0, 20),
                question: question,
                user_id: currentUserId
            })
        });
        
        if (!response.ok) {
            botTextPara.innerText = "Error processing request framework.";
            return;
        }

        // Initialize Reader to parse stream blocks chunk-by-chunk
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        botTextPara.innerText = ""; // Clear loader placeholder string

        let accumulatedAnswer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunkText = decoder.decode(value);
            const lines = chunkText.split("\n");
            
            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const rawJson = line.replace("data: ", "").trim();
                        if (!rawJson) continue;
                        const dataData = JSON.parse(rawJson);
                        
                        // Handle streaming words text updates
                        if (dataData.text) {
                            accumulatedAnswer += dataData.text;
                            botTextPara.innerText = accumulatedAnswer;
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                        
                        // Handle final sources metadata attachment package
                        if (dataData.sources && dataData.sources.length > 0) {
                            let sourcesHtml = `<div style="margin-top: 8px; font-size: 12px; color: #89b4fa; border-top: 1px solid #45475a; padding-top: 5px;">🔍 Sources: `;
                            dataData.sources.forEach(src => {
                                sourcesHtml += `<a href="${src}" target="_blank" style="color: #b4befe; text-decoration: underline; margin-right: 8px; display: inline-block;">Link</a>`;
                            });
                            sourcesHtml += `</div>`;
                            botMsgDiv.innerHTML += sourcesHtml;
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    } catch (err) {
                        // Skip framing anomalies silently
                    }
                }
            }
        }

        // Local state updates validation framework map mirror push
        const activeSession = allSessions.find(s => s.id === currentSessionId);
        if (!activeSession) {
            allSessions.unshift({
                id: currentSessionId,
                title: question.substring(0, 18),
                messages: [
                    { role: "user", content: question },
                    { role: "bot", content: accumulatedAnswer }
                ]
            });
        } else {
            activeSession.messages.push({ role: "user", content: question });
            activeSession.messages.push({ role: "bot", content: accumulatedAnswer });
        }
        renderHistoryList();

    } catch (err) {
        botTextPara.innerText = "Network pipeline error timeout.";
    }
}
  
async function deleteSessionFromServer(sessionId) {
    if (!confirm("Are you sure you want to delete this chat session?")) return;
    try {
        const res = await fetch(`/api/session/${sessionId}`, { method: "DELETE" });
        if (res.ok) {
            allSessions = allSessions.filter(s => s.id !== sessionId);
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                createNewChat();
            } else {
                renderHistoryList();
            }
        }
    } catch (e) {
        console.error("Delete operation failure:", e);
    }
}

function appendMessage(sender, text, sources = []) {
    const chatBox = document.getElementById("chat-box");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    
    let contentHtml = `<p>${text}</p>`;
    if (sender === "bot" && sources && sources.length > 0) {
        contentHtml += `<div style="margin-top: 8px; font-size: 12px; color: #89b4fa; border-top: 1px solid #45475a; padding-top: 5px;">🔍 Sources: `;
        sources.forEach(src => {
            contentHtml += `<a href="${src}" target="_blank" style="color: #b4befe; text-decoration: underline; margin-right: 8px; display: inline-block;">Link</a>`;
        });
        contentHtml += `</div>`;
    }
    
    msgDiv.innerHTML = contentHtml;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}