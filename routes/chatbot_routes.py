from flask import Blueprint, request, jsonify
chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json() or {}
    message = data.get('message', '')
    print(f"Received message: {message}")
    lower = message.lower()
    if 'hello' in lower:
        reply = 'Hello! How can I help you?'
    else:
        reply = f'You said: {message}'
    return jsonify({'response': reply})