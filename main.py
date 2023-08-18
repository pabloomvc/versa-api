from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
from functions import get_chat_completion, translate_message, get_message_corrections, translate_word_by_word, get_tutor_message
from datetime import datetime
import requests
from elevenlabs import generate, set_api_key, save



load_dotenv()
FIREBASE_API_CREDS = os.getenv('FIREBASE_API_CREDS')
CLIENT_URL = os.getenv('CLIENT_URL') # "http://localhost:3000"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
NARAKEET_API_KEY = os.getenv("NARAKEET_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# Eleven Labs stuff
set_api_key(os.getenv("ELEVEN_LABS_API_KEY"))

# Firebase stuff
firebase_api_creds = json.loads(FIREBASE_API_CREDS.replace("'", '"'))
cred = credentials.Certificate(firebase_api_creds)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Flask stuff
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Set maximum file size (here 16MB)
cors = CORS(app, origins=CLIENT_URL)

"""
@app.route('/test_endpoint', methods=['GET'])
def test_endpoint():
    response_data = {"result": "you got it!"}
    response = make_response(jsonify(response_data))
    response.headers["Content-Type"] = "application/json"
    return response
"""

# Notion analytics
@app.route('/log_chat', methods=['POST'])
def log_chat():

    user_email = request.json["userEmail"]
    topic = request.json["topic"]
    target_language = request.json["targetLanguage"]

    DATABASE_ID = "82848bda0a7d4505ab52d5115da6d65d"
    create_url = "https://api.notion.com/v1/pages"
    created_date = datetime.now().isoformat()

    headers = {
        "Authorization": "Bearer " + NOTION_TOKEN,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "User": {"title": [{"text": {"content": user_email}}]},
        "Topic": {"select": {"name": topic}},
        "Language": {"select": {"name": target_language}},
        # "Length": { "number": 2.5 },
        "Created": {"date": {"start": created_date, "end": None}}
        }

    payload = {"parent": {"database_id": DATABASE_ID}, "properties": data}
    print("😂😂😂😂 LOOOOGGGINNGG")
    print(payload)
    res = requests.post(create_url, headers=headers, json=payload)
    print("😂😂", res.status_code, res.text)
    res_data = {"response": "chat_logged"}
    response = make_response(jsonify(res_data))
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/create_user', methods=['POST'])
def create_user(): 
    """This will be called when a user creates an account.
    AND temporarily, also when the user logs in (bc i got a bunch of users that already 
    created accounts, but that are not in the db.)
    It'll check if the user exists in the db.
    If it doesn't, it creates the db item with the empty fields
    """
    print("🔥🔥🔥 FUNCTION CALLED")
    user_id = request.json["userId"]
    # Checks if user exists. If not, it creates it.
    doc_ref = db.collection(u'users').document(user_id)
    if not doc_ref.get().to_dict():
        print("🔥🔥🔥 CREATING USER [placeholder cuz atm im not using this, not necessary]")
        # doc_ref.set({"saved_chats": {}, "saved_words":{}})
    res_data = {"response": "create_user_enpoint"}
    response = make_response(jsonify(res_data))
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/get_saved_chats', methods=['GET'])
def get_saved_chats():
    # Getting saved chats from Firebase
    user_id = request.args.get('user_id')
    doc_ref = db.collection(u'users').document(user_id)
    saved_chats = []
    
    for chat in doc_ref.collection("saved_chats").list_documents():
        saved_chats.append(chat.get().to_dict())

    # saved_chats.sort(key=lambda chat_element: chat_element[0]) # change the sort cuz saved_chats is now a list of dicts

    # print("👀👀 Saved chats", saved_chats)
    response = make_response(jsonify(saved_chats))
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/save_chat', methods=['POST'])
def save_chat():
    user_id = request.json["userId"]
    chat = request.json["currentChat"]
    print("⭐⭐ SAVING CHAT", chat)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S:%f")

    if not chat.get("topic"):
        chat["topic"] = "Open Conversation"
    
    chat["timestamp"] = timestamp

    doc_ref = db.collection(u'users').document(user_id)
    doc_ref.collection("saved_chats").document(chat["id"]).set(chat)
    response = make_response(jsonify({"response": "chat was saved"}))
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/unsave_chat', methods=['POST'])
def unsave_chat():
    user_id = request.json["userId"]
    chat_id = request.json["chatId"]
    doc_ref = db.collection(u'users').document(user_id)
    doc_ref.collection("saved_chats").document(chat_id).delete()
    response = make_response(jsonify({"response": "chat was UNsaved"}))
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/send_message', methods=['POST'])
def send_message():
    chat_history = request.json["chatHistory"]
    source_language = request.json["sourceLanguage"]
    target_language = request.json["targetLanguage"]
    current_topic = request.json["currentTopic"] # Create different prompts for each topic.
    print("😊", current_topic)
    is_suggestion = request.json["isSuggestion"]
    ai_message = get_chat_completion(OPENAI_API_KEY, chat_history, current_topic, source_language, target_language, is_suggestion)
    response = make_response(jsonify(ai_message))
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/send_tutor_message', methods=['POST'])
def send_tutor_message():
    target_language = request.json["targetLanguage"]
    current_topic = request.json["currentTopic"]
    tutor_command = request.json["tutorCommand"]
    user_question = request.json["userQuestion"]
    ai_message = get_tutor_message(OPENAI_API_KEY, current_topic, target_language, tutor_command, user_question)
    response = make_response(jsonify(ai_message))
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/handle_streak', methods=['POST'])
def handle_streak():
    user_id = request.json["userId"]
    is_streak = request.json["isStreak"]
    target_language = request.json["targetLanguage"]
    convo_level = request.json["convoLevel"]

    if convo_level == "1": 
        if is_streak: 
            pass
            # streak += 1
        # points += 1 (but on the db ofc, using user_id and target_language)
        # num of convos += 1
    elif convo_level == "2": 
        pass
        # points += 1
    elif convo_level == "3": 
        pass 
        # points += 1
        # and crowns? idk 

    response = make_response(jsonify({}))
    response.headers["Content-Type"] = "application/json"
    return response



@app.route('/get_corrections', methods=['GET'])
def get_corrections():
    user_message = request.args.get('userMessage')
    source_language = request.args.get("sourceLanguage")
    target_language = request.args.get("targetLanguage")
    is_suggestion = request.args.get("isSuggestion")
    corrections = get_message_corrections(OPENAI_API_KEY,user_message, source_language, target_language, is_suggestion)
    # response_data = {"result": corrections}
    response = make_response(jsonify(corrections))
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/get_word_translations', methods=['GET'])
def get_word_translations():
    message = request.args.get('message')
    target_language = request.args.get("targetLanguage")

    print("📆 Getting word by word")
    print("📆📆", f"Message: {message} - Len:{len(message)}")
    print("📆📆", target_language)
    translations = translate_word_by_word(OPENAI_API_KEY, target_language, message)
    response = make_response(jsonify(translations))
    response.headers["Content-Type"] = "application/json"
    return response



    
"""
GETTING AUDIO
"""

@app.route('/get_speech', methods=['GET'])
def get_speech():
    message = request.args.get('message')
    print("✅Getting speech", message)
    voice = 'luigi'
    # text = """Posta al centro della penisola, Roma è anche il principale nodo ferroviario dell'Italia centrale, collegata mediante le linee ad alta velocità con Firenze e Napoli."""
    url = f'https://api.narakeet.com/text-to-speech/m4a?voice={voice}'

    options = {
        'headers': {
            
            'Accept': 'application/octet-stream',
            'Content-Type': 'text/plain',
            'x-api-key': NARAKEET_API_KEY,
        },
        'data': message.encode('utf8')
    }

    result_speech = requests.post(url, **options).content
    response = make_response(result_speech)
    response.headers["Content-Type"] = "audio/mpeg"
    return response

    # with open('output.m4a', 'wb') as f:
    #     f.write(requests.post(url, **options).content)



@app.route('/receiving_recording', methods=['POST'])
def receiving_recording():
    print("♥️ THE ENDPOINT HAS BEEN HIT")
    print("JSON:", request.json["data"])
    print("files:", request.files)
    print("keys:", request.form.keys())
    print("items:", request.form.items())
    
    #audio_file = request.files["audio-file"]
    """print(request.files)
    audio_file = request.files['audio-file']

    # You can now process the audio file as needed.
    # For example, save it to disk:
    audio_file.save('uploaded_audio.wav')"""
    response = make_response(jsonify({"response":"hiiiii"}))
    response.headers["Content-Type"] = "application/json"
    return response


@app.route('/get_voice_file', methods=['GET'])
def get_voice_file():

    text = request.args.get('text')
    print(f"⭐ Obteniendo: {text}")
    audio = generate(
    text=text,
    voice="Charlotte",
    model="eleven_multilingual_v1")
    # save(audio, "FILE.mp3")
    
    # Create a response containing the audio bytes.
    response = make_response(audio)
    response.headers.set('Content-Type', 'audio/mpeg')
    response.headers.set('Content-Disposition', 'attachment', filename='audio.mp3')

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
