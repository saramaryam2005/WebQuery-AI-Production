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
        if (authOverlay) authOverlay.style.display = "none";
        if (logoutBtn) logoutBtn.style.display = "block";
        fetchHistoryFromServer();
    } else {
        // User logged out hai: Form dikhao, Logout chupao
        if (authOverlay) authOverlay.style.display = "flex";
        if (logoutBtn) logoutBtn.style.display = "none";
    }

    // Enter key press support for prompt box
    const userInput = document.getElementById("user-input");
    if (userInput) {
        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});

// --- SIGNUP PROCESS TRIGGER ---
const btnSignup = document.getElementById("btn-signup");
if (btnSignup) {
    btnSignup.addEventListener("click", async () => {
        const emailEl = document.getElementById("auth-email");
        const passEl = document.getElementById("auth-password");
        const errorEl = document.getElementById("auth-error");

        const email = emailEl ? emailEl.value.trim() : "";
        const password = passEl ? passEl.value.trim() : "";

        if (!email || !password) {
            if (errorEl) {
                errorEl.innerText = "Please fill in all details.";
                errorEl.style.display = "block";
            }
            return;
        }

        try {
            const res = await fetch("/api/auth/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json().catch(() => ({}));

            if (res.ok) {
                alert("Account created successfully! Please click 'Login' now.");
                if (errorEl) errorEl.style.display = "none";
            } else {
                if (errorEl) {
                    errorEl.innerText = data.detail || "Signup failed. Please try again.";
                    errorEl.style.display = "block";
                }
            }
        } catch (e) {
            console.error("Signup network error:", e);
            if (errorEl) {
                errorEl.innerText = "Backend communication failed.";
                errorEl.style.display = "block";
            }
        }
    });
}

// --- LOGIN PROCESS TRIGGER ---
const btnLogin = document.getElementById("btn-login");
if (btnLogin) {
    btnLogin.addEventListener("click", async () => {
        const emailEl = document.getElementById("auth-email");
        const passEl = document.getElementById("auth-password");
        const errorEl = document.getElementById("auth-error");

        const email = emailEl ? emailEl.value.trim() : "";
        const password = passEl ? passEl.value.trim() : "";

        if (!email || !password) {
            if (errorEl) {
                errorEl.innerText = "Please enter email and password.";
                errorEl.style.display = "block";
            }
            return;
        }

        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json().catch(() => ({}));

            if (res.ok) {
                localStorage.setItem("chat_user_id", data.user_id || email);
                if (data.access_token) {
                    localStorage.setItem("chat_token", data.access_token);
                }

                const authOverlay = document.getElementById("auth-overlay");
                if (authOverlay) authOverlay.style.display = "none";
                window.location.reload();
            } else {
                if (errorEl) {
                    errorEl.innerText = data.detail || "Invalid email or password.";
                    errorEl.style.display = "block";
                }
            }
        } catch (e) {
            console.error("Login network error:", e);
            if (errorEl) {
                errorEl.innerText = "Backend communication failed.";
                errorEl.style.display = "block";
            }
        }
    });
}

// --- LOGOUT PROCESS TRIGGER ---
const btnLogout = document.getElementById("btn-logout");
if (btnLogout) {
    btnLogout.addEventListener("click", () => {
        localStorage.removeItem("chat_user_id");
        localStorage.removeItem("chat_token");
        window.location.reload();
    });
}

// --- CHAT HISTORY INTEGRATION LAYER ---
async function fetchHistoryFromServer() {
    if (!currentUserId) return;
    try {
        const response = await fetch(`/api/history?user_id=${encodeURIComponent(currentUserId)}`);
        let data = await response.json().catch(() => []);

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
    if (!listEl) return;
    listEl.innerHTML = "";

    allSessions.forEach(session => {
        const item = document.createElement("li");
        item.className = `history-item ${session.id === currentSessionId ? "active" : ""}`;
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
    if (!chatBox) return;
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
    const chatBox = document.getElementById("chat-box");
    if (chatBox) {
        chatBox.innerHTML = `
            <div class="message bot">
                <p>Hello! 👋 I'm your smart assistant. Ask me anything about our services, products, or technologies! 🚀</p>
            </div>
        `;
    }
    renderHistoryList();
}

async function sendMessage() {
    const inputEl = document.getElementById("user-input");
    const question = inputEl.value.trim();
    if (!question || !currentUserId) return;
    
    appendMessage("user", question);
    inputEl.value = "";
    
    const chatBox = document.getElementById("chat-box");
    
    // Create bot message bubble with Thinking state
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

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let accumulatedAnswer = "";
        let streamBuffer = ""; 
        let isFirstChunk = true; // Thinking text ko replace karne ke liye flag

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            // Append current chunk to buffer stream
            streamBuffer += decoder.decode(value, { stream: true });
            const lines = streamBuffer.split("\n");
            
            // Keep the last element (potentially partial line) in the buffer
            streamBuffer = lines.pop();
            
            for (const line of lines) {
                let cleanLine = line.trim();
                if (cleanLine.startsWith("data: ")) {
                    try {
                        const rawJson = cleanLine.replace("data: ", "").trim();
                        if (!rawJson) continue;
                        const dataData = JSON.parse(rawJson);
                        
                        // Handle streaming words text updates
                        if (dataData.text) {
                            if (isFirstChunk) {
                                botTextPara.innerText = ""; // Pehla chunk aane par Thinking hatao
                                isFirstChunk = false;
                            }
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
                        // Ignore parsing exceptions for incomplete json chunks
                    }
                }
            }
        }

        // Final safe fallback if buffer has leftover characters
        if (streamBuffer.startsWith("data: ")) {
            try {
                const finalJson = streamBuffer.replace("data: ", "").trim();
                const finalData = JSON.parse(finalJson);
                if (finalData.text) {
                    if (isFirstChunk) {
                        botTextPara.innerText = "";
                        isFirstChunk = false;
                    }
                    accumulatedAnswer += finalData.text;
                    botTextPara.innerText = accumulatedAnswer;
                }
            } catch(e) {}
        }

        // Update local session state
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
        console.error(err);
        botTextPara.innerText = "Network pipeline error timeout.";
    }
}

async function deleteSessionFromServer(sessionId) {
    if (!confirm("Are you sure you want to delete this chat session?")) return;
    try {
        const res = await fetch(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
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
    if (!chatBox) return;

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