from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from functions import get_chat_completion, translate_message, get_message_corrections

load_dotenv()
CLIENT_URL = os.getenv('CLIENT_URL') # "http://localhost:3000"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Flask stuff
app = Flask(__name__)
cors = CORS(app, origins=CLIENT_URL)

"""
@app.route('/test_endpoint', methods=['GET'])
def test_endpoint():
    response_data = {"result": "you got it!"}
    response = make_response(jsonify(response_data))
    response.headers["Content-Type"] = "application/json"
    return response
"""

@app.route('/send_message', methods=['POST'])
def send_message():
    chat_history = request.json["chatHistory"]
    source_language = request.json["sourceLanguage"]
    target_language = request.json["targetLanguage"]
    current_topic = request.json["currentTopic"] # Create different prompts for each topic.
    is_suggestion = request.json["isSuggestion"]
    print("⚠️⚠️", current_topic)
    print(is_suggestion)
    ai_message = get_chat_completion(OPENAI_API_KEY, chat_history, current_topic, source_language, target_language, is_suggestion)
    response = make_response(jsonify(ai_message))
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/get_corrections', methods=['GET'])
def get_corrections():
    user_message = request.args.get('userMessage')
    source_language = request.args.get("sourceLanguage")
    target_language = request.args.get("targetLanguage")
    is_suggestion = request.args.get("isSuggestion")
    print(f"🔥 Getting corrections, you know it dawg! is_suggestion {is_suggestion}")
    corrections = get_message_corrections(OPENAI_API_KEY,user_message, source_language, target_language, is_suggestion)
    # response_data = {"result": corrections}
    response = make_response(jsonify(corrections))
    response.headers["Content-Type"] = "application/json"
    return response










@app.route('/translate', methods=['POST'])
def translate():
    message = request.json["messageContent"]
    source_language = request.json["sourceLanguage"]
    target_language = request.json["targetLanguage"]
    print(f"SOURCE {source_language} | TARGET {target_language}")
    translation = translate_message(message, from_=target_language, to=source_language)
    response = make_response(jsonify({"translation": translation}))
    response.headers["Content-Type"] = "application/json"
    return response




if __name__ == "__main__":
    # host="0.0.0.0", port=5000
    app.run()
