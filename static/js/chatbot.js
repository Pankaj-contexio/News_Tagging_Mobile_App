document.addEventListener('DOMContentLoaded', function() {
    const messagesDiv = document.getElementById('chatbot-messages');
    const form = document.getElementById('chatbot-form');
    const input = document.getElementById('chatbot-input');

    function addMessage(text, cls) {
        const msg = document.createElement('div');
        msg.className = 'message ' + cls;
        msg.textContent = text;
        messagesDiv.appendChild(msg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        addMessage(text, 'user');
        input.value = '';
        fetch('/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
        .then(resp => resp.json())
        .then(data => addMessage(data.response, 'bot'))
        .catch(() => addMessage('Error contacting chatbot.', 'bot'));
    });
});