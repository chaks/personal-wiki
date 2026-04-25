// static/app.js
// Configure marked for better output
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        try {
            return hljs.highlightAuto(code).value;
        } catch (e) {
            return code;
        }
    }
});

function renderMarkdown(text) {
    return DOMPurify.sanitize(marked.parse(text));
}

const messagesContainer = document.getElementById('messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

let isStreaming = false;

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    if (type === 'user') {
        messageDiv.textContent = content;
    } else {
        messageDiv.innerHTML = renderMarkdown(content);
        messageDiv.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    }
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return messageDiv;
}

async function sendMessage(message) {
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
    });

    if (!response.ok) {
        throw new Error('Server error');
    }

    return response.body;
}

async function handleChat(message) {
    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.disabled = true;
    sendButton.disabled = true;

    const assistantMessage = document.createElement('div');
    assistantMessage.className = 'message assistant';
    assistantMessage.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    messagesContainer.appendChild(assistantMessage);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    let fullResponse = '';

    try {
        const stream = await sendMessage(message);
        const reader = stream.getReader();
        const decoder = new TextDecoder();

        assistantMessage.innerHTML = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.text) {
                            fullResponse += parsed.text;
                            assistantMessage.innerHTML = renderMarkdown(fullResponse);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                    } catch (e) {
                        // Ignore JSON parse errors for partial chunks
                    }
                }
            }
        }
    } catch (error) {
        assistantMessage.className = 'message error';
        assistantMessage.textContent = `Error: ${error.message}`;
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (message && !isStreaming) {
        handleChat(message);
    }
});

messageInput.focus();
