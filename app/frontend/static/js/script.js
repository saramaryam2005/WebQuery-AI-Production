const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-btn");

function addMessage(text, sender) {
    const message = document.createElement("div");
    message.className = `message ${sender}-message`;

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    message.appendChild(content);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;

    return message;
}

sendButton.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

async function sendMessage() {
    const question = userInput.value.trim();
    if (question === "") return;

    addMessage(question, "user");
    userInput.value = "";
    sendButton.disabled = true;

    let thinkingMessage = addMessage("Thinking...", "bot");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });

        if (!response.ok) {
            throw new Error("Request failed");
        }

        const data = await response.json();
        
        // Target the correct .message-content class instead of 'p'
        thinkingMessage.querySelector(".message-content").textContent = data.answer;

    } catch (error) {
        console.error(error);
        
        // FIXED: Safely targets the correct class to show the error message
        if (thinkingMessage) {
            thinkingMessage.querySelector(".message-content").textContent =
                "Sorry, something went wrong. Please try again.";
        } else {
            addMessage("Sorry, something went wrong. Please try again.", "bot");
        }
    } finally {
        sendButton.disabled = false;
    }
}